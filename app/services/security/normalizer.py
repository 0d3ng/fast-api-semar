"""Normalize SBOM (SPDX), CVE JSON, SARIF 2.1.0, and config-check reports into unified Findings."""

import hashlib
from typing import Dict, Any, List, Optional, Tuple

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _normalize_severity(raw: Optional[str], cvss: Optional[float] = None) -> str:
    if raw:
        val = str(raw).strip().lower()
        mapping = {
            "critical": "critical",
            "crit": "critical",
            "high": "high",
            "error": "high",
            "medium": "medium",
            "moderate": "medium",
            "warning": "medium",
            "low": "low",
            "note": "low",
            "info": "info",
            "informational": "info",
        }
        if val in mapping:
            return mapping[val]
    if cvss is not None:
        if cvss >= 9.0:
            return "critical"
        if cvss >= 7.0:
            return "high"
        if cvss >= 4.0:
            return "medium"
        return "low"
    return "medium"


def make_finding_id(category: str, rule_or_cve: str, target: str, line: Optional[int] = None) -> str:
    """Compute stable deterministic fingerprint ID across builds."""
    raw = f"{category}|{rule_or_cve}|{target}|{line if line is not None else ''}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"F-{digest}"


def parse_spdx_sbom(sbom_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract component list and SBOM metadata coverage from SPDX 2.2 JSON."""
    if not sbom_data or not isinstance(sbom_data, dict):
        return {"components": 0, "with_version_or_cpe": 0, "sbom_coverage": 0.0, "packages": []}

    packages = sbom_data.get("packages") or []
    parsed = []
    covered = 0
    for pkg in packages:
        name = pkg.get("name") or ""
        version = pkg.get("versionInfo")
        cpes = [
            ref.get("referenceLocator")
            for ref in (pkg.get("externalRefs") or [])
            if ref.get("referenceType") in ("cpe22Type", "cpe23Type") and ref.get("referenceLocator")
        ]
        if version or cpes:
            covered += 1
        parsed.append({
            "name": name,
            "version": version,
            "cpe": cpes[0] if cpes else None,
        })

    total = len(parsed)
    coverage = round((covered / total) * 100.0, 2) if total > 0 else 0.0
    return {
        "components": total,
        "with_version_or_cpe": covered,
        "sbom_coverage": coverage,
        "packages": parsed,
    }


def _extract_cvss(vuln: Dict[str, Any]) -> Optional[float]:
    for key in ("cvss", "cvss_score", "baseScore"):
        if vuln.get(key) is not None:
            try:
                return float(vuln[key])
            except (TypeError, ValueError):
                pass
    for item in vuln.get("cvss") or [] if isinstance(vuln.get("cvss"), list) else []:
        metrics = item.get("metrics") or {}
        if metrics.get("baseScore") is not None:
            return float(metrics["baseScore"])
    return None


def parse_cve_reports(cve_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse CVE outputs from esp-idf-sbom check JSON or Grype JSON."""
    findings: List[Dict[str, Any]] = []
    for doc in cve_docs:
        if not isinstance(doc, dict):
            continue

        # Format A: Grype JSON (`matches`)
        for match in doc.get("matches") or []:
            vuln = match.get("vulnerability") or {}
            artifact = match.get("artifact") or {}
            cve_id = vuln.get("id") or "UNKNOWN-CVE"
            comp_name = artifact.get("name") or "unknown"
            comp_ver = artifact.get("version")
            cpes = artifact.get("cpes") or []
            cvss = _extract_cvss(vuln)
            sev = _normalize_severity(vuln.get("severity"), cvss)
            fid = make_finding_id("dependency_cve", cve_id, comp_name)
            findings.append({
                "fid": fid,
                "tool": "grype",
                "tools": ["grype"],
                "category": "dependency_cve",
                "rule_id": cve_id,
                "cve": cve_id,
                "cwe": None,
                "severity": sev,
                "cvss": cvss,
                "epss": None,
                "kev": False,
                "title": f"{cve_id} in {comp_name}",
                "description": (vuln.get("description") or "")[:500],
                "component": {"name": comp_name, "version": comp_ver, "cpe": cpes[0] if cpes else None},
                "location": None,
                "snippet": None,
            })

        # Format B: esp-idf-sbom check JSON (`records` or `vulnerabilities` or `packages`)
        records = doc.get("records") or doc.get("vulnerabilities") or []
        for rec in records:
            if isinstance(rec, dict) and rec.get("vulnerable") is False:
                continue
            cve_id = rec.get("cve_id") or rec.get("id") or "UNKNOWN-CVE"
            comp_name = rec.get("pkg_name") or rec.get("package") or rec.get("component") or "unknown"
            comp_ver = rec.get("pkg_version") or rec.get("version")
            cpe = rec.get("cpe")
            cvss = _extract_cvss(rec)
            sev = _normalize_severity(rec.get("severity"), cvss)
            fid = make_finding_id("dependency_cve", cve_id, comp_name)
            findings.append({
                "fid": fid,
                "tool": "esp-idf-sbom",
                "tools": ["esp-idf-sbom"],
                "category": "dependency_cve",
                "rule_id": cve_id,
                "cve": cve_id,
                "cwe": None,
                "severity": sev,
                "cvss": cvss,
                "epss": None,
                "kev": False,
                "title": f"{cve_id} in {comp_name}",
                "description": (rec.get("cve_desc") or rec.get("description") or "")[:500],
                "component": {"name": comp_name, "version": comp_ver, "cpe": cpe},
                "location": None,
                "snippet": None,
            })

    return findings


def _infer_sarif_category(tool_name: str, rule_id: str) -> str:
    tl = tool_name.lower()
    rl = rule_id.lower()
    if "gitleaks" in tl or "secret" in rl or "password" in rl or "token" in rl or "private-key" in rl:
        return "secret"
    return "code"


def parse_sarif_reports(sarif_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse SARIF 2.1.0 documents (Semgrep, Flawfinder, Gitleaks)."""
    findings: List[Dict[str, Any]] = []
    for doc in sarif_docs:
        if not isinstance(doc, dict):
            continue
        for run in doc.get("runs") or []:
            driver = (run.get("tool") or {}).get("driver") or {}
            tool_name = (driver.get("name") or "sast").lower()
            rules_meta = {
                r.get("id"): r
                for r in (driver.get("rules") or [])
                if isinstance(r, dict) and r.get("id")
            }

            for res in run.get("results") or []:
                rule_id = res.get("ruleId") or "unknown-rule"
                meta = rules_meta.get(rule_id, {})
                props = {**(meta.get("properties") or {}), **(res.get("properties") or {})}

                raw_sev = props.get("security-severity") or props.get("severity") or res.get("level")
                cvss_val = None
                if isinstance(raw_sev, (int, float)) or (isinstance(raw_sev, str) and raw_sev.replace(".", "", 1).isdigit()):
                    cvss_val = float(raw_sev)
                    raw_sev = None

                sev = _normalize_severity(raw_sev, cvss_val)
                cwe = None
                tags = props.get("tags") or []
                for tag in tags:
                    if isinstance(tag, str) and "CWE-" in tag.upper():
                        cwe = tag.upper().split("/")[-1]
                        if not cwe.startswith("CWE-"):
                            idx = cwe.find("CWE-")
                            cwe = cwe[idx:] if idx >= 0 else cwe
                        break

                locs = res.get("locations") or []
                file_path = "unknown"
                line = None
                snippet = None
                if locs:
                    phys = (locs[0].get("physicalLocation") or {})
                    file_path = (phys.get("artifactLocation") or {}).get("uri") or "unknown"
                    region = phys.get("region") or {}
                    line = region.get("startLine")
                    snippet = ((region.get("snippet") or {}).get("text") or "")[:600] or None

                category = _infer_sarif_category(tool_name, rule_id)
                fid = make_finding_id(category, rule_id, file_path, line)
                msg = ((res.get("message") or {}).get("text") or "")[:500]
                findings.append({
                    "fid": fid,
                    "tool": tool_name,
                    "tools": [tool_name],
                    "category": category,
                    "rule_id": rule_id,
                    "cve": None,
                    "cwe": cwe,
                    "severity": sev,
                    "cvss": cvss_val,
                    "epss": None,
                    "kev": False,
                    "title": f"{rule_id} at {file_path}:{line or '?'}",
                    "description": msg,
                    "component": None,
                    "location": {"file": file_path, "line": line},
                    "snippet": snippet,
                })

    return findings


def parse_config_reports(config_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse custom sdkconfig/transport configuration findings."""
    findings: List[Dict[str, Any]] = []
    for doc in config_docs:
        if not isinstance(doc, dict):
            continue
        for item in doc.get("findings") or []:
            rule_id = item.get("rule_id") or "CONFIG_ISSUE"
            file_path = item.get("file") or "sdkconfig"
            line = item.get("line")
            fid = make_finding_id("config", rule_id, file_path, line)
            findings.append({
                "fid": fid,
                "tool": item.get("tool") or "sdkconfig-checker",
                "tools": [item.get("tool") or "sdkconfig-checker"],
                "category": "config",
                "rule_id": rule_id,
                "cve": None,
                "cwe": item.get("cwe"),
                "severity": _normalize_severity(item.get("severity")),
                "cvss": None,
                "epss": None,
                "kev": False,
                "title": item.get("title") or rule_id,
                "description": (item.get("description") or "")[:500],
                "component": None,
                "location": {"file": file_path, "line": line},
                "snippet": item.get("snippet"),
            })
    return findings


def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge duplicate findings sharing the same fid across scanners."""
    by_fid: Dict[str, Dict[str, Any]] = {}
    for f in findings:
        fid = f["fid"]
        if fid not in by_fid:
            by_fid[fid] = f
            continue
        existing = by_fid[fid]
        for t in f.get("tools") or [f["tool"]]:
            if t not in existing["tools"]:
                existing["tools"].append(t)
        if SEVERITY_ORDER.get(f["severity"], 0) > SEVERITY_ORDER.get(existing["severity"], 0):
            existing["severity"] = f["severity"]
        if f.get("cvss") is not None and (existing.get("cvss") is None or f["cvss"] > existing["cvss"]):
            existing["cvss"] = f["cvss"]
        if not existing.get("description") and f.get("description"):
            existing["description"] = f["description"]
        if not existing.get("snippet") and f.get("snippet"):
            existing["snippet"] = f["snippet"]

    result = list(by_fid.values())
    result.sort(
        key=lambda x: (
            SEVERITY_ORDER.get(x.get("severity", "info"), 0),
            x.get("cvss") or 0.0,
        ),
        reverse=True,
    )
    return result


def build_summary(sbom_meta: Dict[str, Any], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute counts by category and severity for dashboard & policy metrics."""
    cves_by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    static_by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    secrets_count = 0
    config_count = 0

    for f in findings:
        sev = f.get("severity", "medium")
        cat = f.get("category")
        if cat == "dependency_cve":
            cves_by_sev[sev] = cves_by_sev.get(sev, 0) + 1
        elif cat == "code":
            static_by_sev[sev] = static_by_sev.get(sev, 0) + 1
        elif cat == "secret":
            secrets_count += 1
        elif cat == "config":
            config_count += 1

    return {
        "components": sbom_meta.get("components", 0),
        "sbom_coverage": sbom_meta.get("sbom_coverage", 0.0),
        "total_findings": len(findings),
        "cves_by_sev": cves_by_sev,
        "static_by_sev": static_by_sev,
        "secrets_count": secrets_count,
        "config_issues": config_count,
    }


def compute_diff(
    current_findings: List[Dict[str, Any]],
    previous_assessment: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Compare finding fingerprints with the previous assessment of the same platform."""
    if not previous_assessment:
        return None
    prev_fids = {f["fid"] for f in (previous_assessment.get("findings") or []) if f.get("fid")}
    curr_fids = {f["fid"] for f in current_findings if f.get("fid")}

    return {
        "previous_assessment_id": str(previous_assessment.get("_id")),
        "previous_version": previous_assessment.get("target_version"),
        "new": sorted(curr_fids - prev_fids),
        "resolved": sorted(prev_fids - curr_fids),
        "persisting": sorted(curr_fids & prev_fids),
    }


def normalize_evidence_bundle(
    sbom_data: Optional[Dict[str, Any]],
    cve_docs: List[Dict[str, Any]],
    sarif_docs: List[Dict[str, Any]],
    config_docs: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Run all normalizers, deduplicate, and return (sbom_meta, findings, summary)."""
    sbom_meta = parse_spdx_sbom(sbom_data)
    raw: List[Dict[str, Any]] = []
    raw.extend(parse_cve_reports(cve_docs))
    raw.extend(parse_sarif_reports(sarif_docs))
    raw.extend(parse_config_reports(config_docs))
    findings = deduplicate_findings(raw)
    summary = build_summary(sbom_meta, findings)
    return sbom_meta, findings, summary

