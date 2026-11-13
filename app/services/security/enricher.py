"""Vulnerability enrichment (EPSS, CISA KEV) and sdkconfig reachability hints."""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set

import httpx
import pytz

from app.utils.config import SECURITY_ENRICH_NETWORK
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)

EPSS_API_URL = "https://api.first.org/data/v1/epss"
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CACHE_TTL_HOURS = 24


async def _get_cached_kev_set() -> Set[str]:
    try:
        cached = await db.security_intel_cache.find_one({"_id": "cisa_kev"})
        now = datetime.now(tz=pytz.UTC)
        if cached and cached.get("updated_at"):
            ts = cached["updated_at"]
            if ts.tzinfo is None:
                ts = pytz.UTC.localize(ts)
            if now - ts < timedelta(hours=CACHE_TTL_HOURS):
                return set(cached.get("cves") or [])
    except Exception:
        pass

    if not SECURITY_ENRICH_NETWORK:
        return set()

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(CISA_KEV_URL)
            if resp.status_code == 200:
                vulns = resp.json().get("vulnerabilities") or []
                cves = sorted({v.get("cveID") for v in vulns if v.get("cveID")})
                try:
                    await db.security_intel_cache.update_one(
                        {"_id": "cisa_kev"},
                        {"$set": {"cves": cves, "updated_at": datetime.now(tz=pytz.UTC)}},
                        upsert=True,
                    )
                except Exception:
                    pass
                return set(cves)
    except Exception as exc:
        logger.debug(f"CISA KEV fetch skipped/failed: {exc}")
    return set()


async def _fetch_epss_scores(cve_ids: List[str]) -> Dict[str, float]:
    if not cve_ids or not SECURITY_ENRICH_NETWORK:
        return {}
    scores: Dict[str, float] = {}
    try:
        batch = ",".join(cve_ids[:50])
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(EPSS_API_URL, params={"cve": batch})
            if resp.status_code == 200:
                for item in resp.json().get("data") or []:
                    cve = item.get("cve")
                    if cve and item.get("epss") is not None:
                        scores[cve] = round(float(item["epss"]), 4)
    except Exception as exc:
        logger.debug(f"EPSS fetch skipped/failed: {exc}")
    return scores


def _compute_reachability_hint(
    finding: Dict[str, Any],
    sdkconfig_flags: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not sdkconfig_flags:
        return None
    comp_name = ((finding.get("component") or {}).get("name") or "").lower()
    loc_file = ((finding.get("location") or {}).get("file") or "").lower()
    text = f"{comp_name} {loc_file} {finding.get('title', '').lower()}"

    if any(k in text for k in ("bt", "bluetooth", "nimble", "bluedroid")) and sdkconfig_flags.get("CONFIG_BT_ENABLED") is False:
        return "Component/module disabled in sdkconfig (CONFIG_BT_ENABLED is not set)"
    if "lwip" in text and sdkconfig_flags.get("CONFIG_LWIP_IPV6") is False and "ipv6" in finding.get("description", "").lower():
        return "IPv6 disabled in sdkconfig (CONFIG_LWIP_IPV6 is not set)"
    return None


async def enrich_findings(
    findings: List[Dict[str, Any]],
    sdkconfig_flags: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Enrich CVE findings with EPSS, CISA KEV, and sdkconfig reachability hints."""
    cve_ids = sorted({
        f["cve"] for f in findings
        if f.get("category") == "dependency_cve" and f.get("cve") and str(f["cve"]).startswith("CVE-")
    })

    kev_set: Set[str] = set()
    epss_map: Dict[str, float] = {}
    if cve_ids:
        kev_set = await _get_cached_kev_set()
        epss_map = await _fetch_epss_scores(cve_ids)

    for f in findings:
        cve = f.get("cve")
        if cve:
            if cve in kev_set:
                f["kev"] = True
            if cve in epss_map and f.get("epss") is None:
                f["epss"] = epss_map[cve]
        hint = _compute_reachability_hint(f, sdkconfig_flags)
        if hint:
            f["reachable_hint"] = hint

    return findings

