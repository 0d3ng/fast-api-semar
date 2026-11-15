"""Service for firmware security assessment ingestion, AI analysis, review, and OTA gating."""

import hashlib
import json
import os
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

import pytz
from bson import ObjectId
from fastapi import HTTPException, UploadFile

from app.models.ota_security_assessment import SecurityAssessment
from app.schemas.ota_security_assessment_schema import (
    AssessmentSourceMetadata,
    AssessmentReviewRequest,
    AssessmentReanalyzeRequest,
    SecurityAssessmentResponse,
)
from app.services.security.ai_analyzer import analyze_findings_with_ai
from app.services.security.decision import merge_policy_and_ai, workflow_state_for_decision
from app.services.security.enricher import apply_reachability, enrich_findings
from app.services.security.github_issue_client import create_fix_issue
from app.services.security.normalizer import compute_diff, normalize_evidence_bundle
from app.services.security.policy_engine import evaluate_policy
from app.utils.config import (
    FIRMWARE_FOLDER,
    SECURITY_GATE_MODE,
    SECURITY_POLICY_PROFILE,
)
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_json_bytes(raw: bytes, filename: str) -> Dict[str, Any]:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in evidence file '{filename}': {exc}")


def _save_evidence_file(target_version: str, filename: str, raw: bytes) -> str:
    safe_ver = target_version.replace("/", "_").replace("\\", "_")
    safe_name = os.path.basename(filename)
    storage_dir = os.path.join(FIRMWARE_FOLDER or "firmware", "security", safe_ver)
    os.makedirs(storage_dir, exist_ok=True)
    path = os.path.join(storage_dir, safe_name)
    with open(path, "wb") as f:
        f.write(raw)
    return path


class SecurityGate:
    """Enforces pre-broadcast security policy and human approval checks."""

    @staticmethod
    async def check(
        target_version: str,
        platform_type: Optional[str] = None,
        target_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        mode = (SECURITY_GATE_MODE or "monitor").strip().lower()
        if mode == "off":
            return {"allowed": True, "mode": "off", "reason": "Security gate disabled"}

        query: Dict[str, Any] = {
            "target_version": target_version,
            "deleted_at": None,
        }
        if platform_type:
            query["platform_type"] = platform_type

        assessment = await db.ota_security_assessments.find_one(
            query,
            sort=[("inserted_at", -1)],
        )

        if not assessment:
            detail = {
                "gate": "security_assessment",
                "decision": "MISSING",
                "message": f"No security assessment found for {target_version} ({platform_type or 'any'})",
            }
            if mode == "enforce":
                raise HTTPException(status_code=409, detail=detail)
            logger.warning(f"[MONITOR GATE] {detail['message']}")
            return {"allowed": True, "mode": mode, **detail}

        if target_hash and assessment.get("target_hash") != target_hash:
            detail = {
                "gate": "security_assessment",
                "assessment_id": str(assessment["_id"]),
                "decision": "HASH_MISMATCH",
                "message": "Security assessment target_hash does not match release binary hash",
            }
            if mode == "enforce":
                raise HTTPException(status_code=409, detail=detail)
            logger.warning(f"[MONITOR GATE] {detail['message']}")
            return {"allowed": True, "mode": mode, **detail}

        status = assessment.get("status")
        decision = assessment.get("final_decision")
        wf_state = assessment.get("workflow_state")

        if status in ("received", "analyzing"):
            detail = {
                "gate": "security_assessment",
                "assessment_id": str(assessment["_id"]),
                "decision": "ANALYZING",
                "message": "Security assessment is still running",
            }
            if mode == "enforce":
                raise HTTPException(status_code=409, detail=detail)
            return {"allowed": True, "mode": mode, **detail}

        is_allowed = (wf_state == "approved") or (decision == "PASS" and wf_state != "blocked")
        if is_allowed:
            return {
                "allowed": True,
                "mode": mode,
                "assessment_id": str(assessment["_id"]),
                "decision": decision,
                "workflow_state": wf_state,
            }

        triggered = [r.get("rule_id") for r in (assessment.get("policy_result") or {}).get("triggered_rules", [])]
        detail = {
            "gate": "security_assessment",
            "assessment_id": str(assessment["_id"]),
            "decision": decision,
            "workflow_state": wf_state,
            "triggered_rules": triggered,
            "message": f"Broadcast blocked by security gate: decision={decision}, state={wf_state}",
        }
        if mode == "enforce":
            raise HTTPException(status_code=409, detail=detail)
        logger.warning(f"[MONITOR GATE] Would block broadcast: {detail}")
        return {"allowed": True, "mode": mode, **detail}


class SecurityAssessmentService:
    @staticmethod
    async def ingest_and_assess(
        metadata: AssessmentSourceMetadata,
        sbom_file: Optional[UploadFile] = None,
        cve_files: Optional[List[UploadFile]] = None,
        sarif_files: Optional[List[UploadFile]] = None,
        config_file: Optional[UploadFile] = None,
        run_ai_sync: bool = False,
        user_id: str = "system",
    ) -> SecurityAssessmentResponse:
        """Ingest CI security evidence, normalize, run policy engine, and run AI analysis."""
        try:
            now_utc = datetime.now(tz=pytz.UTC)
            hasher = hashlib.sha256()
            stored_files: Dict[str, Any] = {"sbom": None, "cve": [], "sarif": [], "config": None}

            sbom_data: Optional[Dict[str, Any]] = None
            if sbom_file:
                raw = await sbom_file.read()
                hasher.update(raw)
                stored_files["sbom"] = _save_evidence_file(metadata.target_version, sbom_file.filename or "sbom.spdx.json", raw)
                sbom_data = _parse_json_bytes(raw, sbom_file.filename or "sbom")

            cve_docs: List[Dict[str, Any]] = []
            for f in cve_files or []:
                raw = await f.read()
                hasher.update(raw)
                path = _save_evidence_file(metadata.target_version, f.filename or "cve.json", raw)
                stored_files["cve"].append(path)
                cve_docs.append(_parse_json_bytes(raw, f.filename or "cve"))

            sarif_docs: List[Dict[str, Any]] = []
            for f in sarif_files or []:
                raw = await f.read()
                hasher.update(raw)
                path = _save_evidence_file(metadata.target_version, f.filename or "scan.sarif", raw)
                stored_files["sarif"].append(path)
                sarif_docs.append(_parse_json_bytes(raw, f.filename or "sarif"))

            config_docs: List[Dict[str, Any]] = []
            if config_file:
                raw = await config_file.read()
                hasher.update(raw)
                stored_files["config"] = _save_evidence_file(metadata.target_version, config_file.filename or "config_findings.json", raw)
                config_docs.append(_parse_json_bytes(raw, config_file.filename or "config"))

            _, findings, summary = normalize_evidence_bundle(sbom_data, cve_docs, sarif_docs, config_docs)
            findings = await enrich_findings(
                findings,
                sdkconfig_flags=metadata.sdkconfig_flags,
                platform_type=metadata.platform_type,
            )
            policy_result = evaluate_policy(findings, summary, profile=SECURITY_POLICY_PROFILE)

            # Find previous assessment for differential tracking & superseding fix_requested
            prev_doc = await db.ota_security_assessments.find_one(
                {
                    "platform_type": metadata.platform_type,
                    "deleted_at": None,
                },
                sort=[("inserted_at", -1)],
            )
            diff = compute_diff(findings, prev_doc)

            # Find matching releases already uploaded
            release_ids: List[str] = []
            rel_cursor = db.ota_firmware_releases.find(
                {
                    "target_version": metadata.target_version,
                    "platform_type": metadata.platform_type,
                    "target_hash": metadata.target_hash,
                    "deleted_at": None,
                }
            )
            async for rdoc in rel_cursor:
                release_ids.append(str(rdoc["_id"]))

            assessment = SecurityAssessment(
                target_version=metadata.target_version,
                platform_type=metadata.platform_type,
                target_hash=metadata.target_hash,
                release_ids=release_ids,
                source={
                    "repo": metadata.repo,
                    "git_commit": metadata.git_commit,
                    "ci_run_id": metadata.ci_run_id,
                    "idf_version": metadata.idf_version,
                    "ota_protocol": metadata.ota_protocol,
                    "sdkconfig_flags": metadata.sdkconfig_flags,
                },
                status="analyzing",
                workflow_state=workflow_state_for_decision(policy_result["decision"]),
                evidence={
                    "bundle_sha256": hasher.hexdigest(),
                    "files": stored_files,
                    "tool_versions": metadata.tool_versions,
                },
                findings=findings,
                summary=summary,
                policy_result=policy_result,
                diff_vs_previous=diff,
                final_decision=policy_result["decision"],
                decision_source="policy",
                supersedes=str(prev_doc["_id"]) if prev_doc else None,
                inserted_at=now_utc,
                inserted_by=user_id,
                updated_at=now_utc,
                updated_by=user_id,
            )

            inserted = await db.ota_security_assessments.insert_one(assessment.model_dump(by_alias=True))
            new_id = str(inserted.inserted_id)

            if prev_doc and prev_doc.get("workflow_state") == "fix_requested":
                await db.ota_security_assessments.update_one(
                    {"_id": prev_doc["_id"]},
                    {"$set": {"workflow_state": "superseded", "superseded_by": new_id, "updated_at": now_utc}},
                )

            if release_ids:
                await db.ota_firmware_releases.update_many(
                    {"_id": {"$in": [ObjectId(rid) for rid in release_ids if ObjectId.is_valid(rid)]}},
                    {"$set": {"security_assessment_id": new_id, "security_decision": policy_result["decision"]}},
                )

            if run_ai_sync:
                return await SecurityAssessmentService.run_ai_stage(new_id)

            created_doc = await db.ota_security_assessments.find_one({"_id": inserted.inserted_id})
            return SecurityAssessmentResponse(**created_doc)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Failed to ingest security assessment: {exc}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(exc))

    @staticmethod
    async def run_ai_stage(
        assessment_id: str,
        model_override: Optional[str] = None,
        profile_override: Optional[str] = None,
        run_ai: bool = True,
    ) -> SecurityAssessmentResponse:
        """Execute AI analysis stage and merge monotonically with policy decision."""
        if not ObjectId.is_valid(assessment_id):
            raise HTTPException(status_code=400, detail="Invalid assessment ID")

        doc = await db.ota_security_assessments.find_one({"_id": ObjectId(assessment_id), "deleted_at": None})
        if not doc:
            raise HTTPException(status_code=404, detail="SecurityAssessment not found")

        try:
            findings = doc.get("findings") or []
            summary = doc.get("summary") or {}
            source_info = doc.get("source") or {}
            findings = apply_reachability(
                findings,
                sdkconfig_flags=source_info.get("sdkconfig_flags"),
                platform_type=doc.get("platform_type") or "esp32",
            )
            policy_result = doc.get("policy_result") or {}
            target_profile = profile_override or policy_result.get("profile") or SECURITY_POLICY_PROFILE
            policy_result = evaluate_policy(findings, summary, profile=target_profile)

            ai_result = None
            if run_ai:
                source_meta = {
                    **source_info,
                    "target_version": doc.get("target_version"),
                    "platform_type": doc.get("platform_type"),
                }
                ai_result = await analyze_findings_with_ai(
                    source_meta=source_meta,
                    findings=findings,
                    summary=summary,
                    policy_result=policy_result,
                    diff_vs_previous=doc.get("diff_vs_previous"),
                    model_override=model_override,
                )

            ai_rec = ai_result.get("recommended_decision") if ai_result else None
            final_decision, decision_source = merge_policy_and_ai(policy_result.get("decision", "REVIEW_REQUIRED"), ai_rec)
            wf_state = workflow_state_for_decision(final_decision)

            now_utc = datetime.now(tz=pytz.UTC)
            update_fields: Dict[str, Any] = {
                "findings": findings,
                "policy_result": policy_result,
                "ai_result": ai_result,
                "final_decision": final_decision,
                "decision_source": decision_source,
                "workflow_state": wf_state,
                "status": "completed",
                "error_message": None,
                "updated_at": now_utc,
            }
            await db.ota_security_assessments.update_one({"_id": doc["_id"]}, {"$set": update_fields})

            await db.ota_firmware_releases.update_many(
                {
                    "target_version": doc.get("target_version"),
                    "platform_type": doc.get("platform_type"),
                    "target_hash": doc.get("target_hash"),
                    "deleted_at": None,
                },
                {"$set": {"security_assessment_id": assessment_id, "security_decision": final_decision}},
            )

            updated = await db.ota_security_assessments.find_one({"_id": doc["_id"]})
            return SecurityAssessmentResponse(**updated)
        except Exception as exc:
            logger.error(f"AI stage failed for {assessment_id}: {exc}\n{traceback.format_exc()}")
            await db.ota_security_assessments.update_one(
                {"_id": doc["_id"]},
                {"$set": {"status": "error", "error_message": str(exc), "updated_at": datetime.now(tz=pytz.UTC)}},
            )
            raise HTTPException(status_code=500, detail=str(exc))

    @staticmethod
    async def list_assessments(
        target_version: Optional[str] = None,
        platform_type: Optional[str] = None,
        final_decision: Optional[str] = None,
        workflow_state: Optional[str] = None,
    ) -> List[SecurityAssessmentResponse]:
        query: Dict[str, Any] = {"deleted_at": None}
        if target_version:
            query["target_version"] = target_version
        if platform_type:
            query["platform_type"] = platform_type
        if final_decision:
            query["final_decision"] = final_decision
        if workflow_state:
            query["workflow_state"] = workflow_state

        results: List[SecurityAssessmentResponse] = []
        cursor = db.ota_security_assessments.find(query).sort("inserted_at", -1)
        async for doc in cursor:
            results.append(SecurityAssessmentResponse(**doc))
        return results

    @staticmethod
    async def get_assessment(assessment_id: str) -> SecurityAssessmentResponse:
        if not ObjectId.is_valid(assessment_id):
            raise HTTPException(status_code=400, detail="Invalid assessment ID")
        doc = await db.ota_security_assessments.find_one({"_id": ObjectId(assessment_id), "deleted_at": None})
        if not doc:
            raise HTTPException(status_code=404, detail="SecurityAssessment not found")
        return SecurityAssessmentResponse(**doc)

    @staticmethod
    async def review_assessment(
        assessment_id: str,
        review_req: AssessmentReviewRequest,
        reviewer_username: str,
        reviewer_id: str,
    ) -> SecurityAssessmentResponse:
        """Process one-step human review: approve, request_fix (+ GitHub Issue), or block."""
        if not ObjectId.is_valid(assessment_id):
            raise HTTPException(status_code=400, detail="Invalid assessment ID")

        doc = await db.ota_security_assessments.find_one({"_id": ObjectId(assessment_id), "deleted_at": None})
        if not doc:
            raise HTTPException(status_code=404, detail="SecurityAssessment not found")

        if doc.get("final_decision") == "BLOCKED" and review_req.action == "approve":
            raise HTTPException(
                status_code=400,
                detail="Cannot approve a BLOCKED assessment; submit a fixed firmware build or choose request_fix/block.",
            )

        now_utc = datetime.now(tz=pytz.UTC)
        issue_info: Optional[Dict[str, Any]] = None
        if review_req.action == "request_fix" and review_req.create_github_issue:
            issue_info = await create_fix_issue(
                assessment=doc,
                reviewer=reviewer_username,
                reason=review_req.reason,
                selected_fids=review_req.selected_fids,
            )

        review_entry: Dict[str, Any] = {
            "reviewer": reviewer_username,
            "reviewer_id": reviewer_id,
            "action": review_req.action,
            "reason": review_req.reason,
            "selected_fids": review_req.selected_fids,
            "ai_rating": review_req.ai_rating,
            "false_positive_fids": review_req.false_positive_fids,
            "github_issue": issue_info,
            "at": now_utc.isoformat(),
        }

        if review_req.action == "approve":
            new_wf = "approved"
            new_decision = "PASS"
        elif review_req.action == "request_fix":
            new_wf = "fix_requested"
            new_decision = doc.get("final_decision", "REVIEW_REQUIRED")
        else:
            new_wf = "blocked"
            new_decision = "BLOCKED"

        update_set: Dict[str, Any] = {
            "workflow_state": new_wf,
            "final_decision": new_decision,
            "decision_source": "human_review",
            "updated_at": now_utc,
            "updated_by": reviewer_id,
        }
        if issue_info and issue_info.get("created"):
            update_set["github_issue_number"] = issue_info.get("number")
            update_set["github_issue_url"] = issue_info.get("url")

        await db.ota_security_assessments.update_one(
            {"_id": doc["_id"]},
            {
                "$set": update_set,
                "$push": {"review_history": review_entry},
            },
        )

        await db.ota_firmware_releases.update_many(
            {
                "target_version": doc.get("target_version"),
                "platform_type": doc.get("platform_type"),
                "target_hash": doc.get("target_hash"),
                "deleted_at": None,
            },
            {"$set": {"security_assessment_id": assessment_id, "security_decision": new_decision}},
        )

        if review_req.action == "approve" and review_req.auto_broadcast:
            from app.services.ota_firmware_release_service import FirmwareReleaseService
            await FirmwareReleaseService.broadcast_firmware(
                target_version=doc["target_version"],
                platform_type=doc.get("platform_type", "esp32"),
                user_id=reviewer_id,
            )

        updated = await db.ota_security_assessments.find_one({"_id": doc["_id"]})
        return SecurityAssessmentResponse(**updated)

