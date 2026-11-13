import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId
from fastapi import HTTPException
from starlette.testclient import TestClient

from app.main import app
from app.schemas.ota_security_assessment_schema import AssessmentReviewRequest
from app.services.ota_security_assessment_service import SecurityAssessmentService, SecurityGate
from app.services.security.ai_analyzer import analyze_findings_with_ai, validate_and_ground_output
from app.services.security.decision import merge_policy_and_ai
from app.services.security.normalizer import compute_diff, normalize_evidence_bundle
from app.services.security.policy_engine import evaluate_policy
from app.utils.config import SEMAR_API_TOKEN

client = TestClient(app)


class TestSecurityNormalizerAndPolicy(unittest.TestCase):
    def test_normalize_and_deduplicate_across_scanners(self):
        sbom = {
            "packages": [
                {"name": "esp-idf", "versionInfo": "6.0.2", "externalRefs": []},
                {"name": "cjson", "versionInfo": "1.7.15", "externalRefs": [{"referenceType": "cpe23Type", "referenceLocator": "cpe:2.3:a:cjson_project:cjson:1.7.15:*:*:*:*:*:*:*"}]},
                {"name": "custom_app", "externalRefs": []},
            ]
        }
        cve_idf = {
            "records": [
                {"cve_id": "CVE-2023-50472", "pkg_name": "cjson", "pkg_version": "1.7.15", "cvss": 7.5, "severity": "high"}
            ]
        }
        cve_grype = {
            "matches": [
                {
                    "vulnerability": {"id": "CVE-2023-50472", "severity": "High", "cvss": [{"metrics": {"baseScore": 7.5}}]},
                    "artifact": {"name": "cjson", "version": "1.7.15", "cpes": []},
                }
            ]
        }
        sarif = {
            "runs": [
                {
                    "tool": {"driver": {"name": "Semgrep", "rules": [{"id": "c.unsafe-strcpy", "properties": {"tags": ["CWE-120"]}}]}},
                    "results": [
                        {
                            "ruleId": "c.unsafe-strcpy",
                            "level": "error",
                            "message": {"text": "Use strlcpy instead of strcpy"},
                            "locations": [{"physicalLocation": {"artifactLocation": {"uri": "main/app_main.c"}, "region": {"startLine": 42, "snippet": {"text": "strcpy(buf, src);"}}}}],
                        }
                    ],
                },
                {
                    "tool": {"driver": {"name": "Gitleaks", "rules": [{"id": "generic-api-key"}]}},
                    "results": [
                        {
                            "ruleId": "generic-api-key",
                            "level": "error",
                            "message": {"text": "Hardcoded API key"},
                            "locations": [{"physicalLocation": {"artifactLocation": {"uri": "components/wifi_manager/wifi_manager.c"}, "region": {"startLine": 12}}}],
                        }
                    ],
                },
            ]
        }
        cfg = {
            "findings": [
                {"rule_id": "SECURE_BOOT_DISABLED", "severity": "medium", "file": "sdkconfig", "line": 100, "title": "Secure Boot disabled"}
            ]
        }

        sbom_meta, findings, summary = normalize_evidence_bundle(sbom, [cve_idf, cve_grype], [sarif], [cfg])
        self.assertEqual(sbom_meta["components"], 3)
        self.assertAlmostEqual(sbom_meta["sbom_coverage"], 66.67, places=2)
        # CVE deduplicated across esp-idf-sbom and grype -> 4 findings total
        self.assertEqual(len(findings), 4)
        cve_finding = next(f for f in findings if f["category"] == "dependency_cve")
        self.assertEqual(sorted(cve_finding["tools"]), ["esp-idf-sbom", "grype"])
        self.assertEqual(summary["secrets_count"], 1)
        self.assertEqual(summary["config_issues"], 1)

    def test_policy_profiles_lab_vs_production(self):
        findings = [
            {"fid": "F-1", "category": "config", "rule_id": "SECURE_BOOT_DISABLED", "severity": "medium"},
            {"fid": "F-2", "category": "config", "rule_id": "ESP_TLS_INSECURE", "severity": "high"},
        ]
        summary = {"components": 10, "sbom_coverage": 100.0}

        lab_res = evaluate_policy(findings, summary, profile="lab")
        prod_res = evaluate_policy(findings, summary, profile="production")

        self.assertEqual(lab_res["decision"], "REVIEW_REQUIRED")
        self.assertEqual(prod_res["decision"], "BLOCKED")
        self.assertTrue(any(w["rule_id"] == "HW_SECURITY_FLAGS_DISABLED" for w in lab_res["warnings"]))

    def test_lab_passes_when_only_hw_flags_disabled(self):
        findings = [{"fid": "F-1", "category": "config", "rule_id": "SECURE_BOOT_DISABLED", "severity": "medium"}]
        summary = {"components": 10, "sbom_coverage": 100.0}
        self.assertEqual(evaluate_policy(findings, summary, profile="lab")["decision"], "PASS")
        self.assertEqual(evaluate_policy(findings, summary, profile="production")["decision"], "REVIEW_REQUIRED")

    def test_compute_diff(self):
        prev = {"_id": ObjectId(), "target_version": "v1", "findings": [{"fid": "F-1"}, {"fid": "F-2"}]}
        curr = [{"fid": "F-2"}, {"fid": "F-3"}]
        diff = compute_diff(curr, prev)
        self.assertEqual(diff["new"], ["F-3"])
        self.assertEqual(diff["resolved"], ["F-1"])
        self.assertEqual(diff["persisting"], ["F-2"])


class TestMonotonicAndAiGrounding(unittest.IsolatedAsyncioTestCase):
    def test_monotonic_decision_merge(self):
        self.assertEqual(merge_policy_and_ai("PASS", "REVIEW_REQUIRED"), ("REVIEW_REQUIRED", "ai_escalation"))
        self.assertEqual(merge_policy_and_ai("PASS", "BLOCKED"), ("REVIEW_REQUIRED", "ai_escalation"))
        self.assertEqual(merge_policy_and_ai("BLOCKED", "PASS"), ("BLOCKED", "policy"))
        self.assertEqual(merge_policy_and_ai("REVIEW_REQUIRED", "PASS"), ("REVIEW_REQUIRED", "policy"))

    def test_grounding_validator_drops_hallucinated_fids(self):
        raw = json.dumps({
            "overall_risk": "medium",
            "recommended_decision": "REVIEW_REQUIRED",
            "confidence": 0.85,
            "triage": [
                {"fid": "F-real1", "relevance": "applicable", "fp_likelihood": 0.1, "rationale": "valid", "evidence_refs": []},
                {"fid": "F-fake999", "relevance": "applicable", "fp_likelihood": 0.2, "rationale": "hallucinated", "evidence_refs": []},
            ],
            "correlations": [
                {"title": "Chain", "severity": "high", "finding_fids": ["F-real1", "F-fake999"], "attack_scenario": "test", "compensating_controls": "ED25519"},
            ],
            "mitigations": [
                {"priority": 1, "finding_fids": ["F-real1"], "action": "Fix strcpy", "target": "main.c:10"},
            ],
            "summary": "One valid finding.",
        })
        out, meta = validate_and_ground_output(raw, {"F-real1"})
        self.assertFalse(meta["grounding_ok"])
        self.assertEqual(meta["rejected_items"], 2)
        self.assertEqual(len(out.triage), 1)
        self.assertEqual(out.correlations[0].finding_fids, ["F-real1"])

    async def test_ai_analyzer_fallback_on_ollama_error(self):
        mock_client = MagicMock()
        mock_client.model = "qwen2.5-coder:14b"
        mock_client.chat_json = AsyncMock(side_effect=RuntimeError("Ollama unreachable"))

        res = await analyze_findings_with_ai(
            source_meta={"target_version": "v1.0.0", "platform_type": "esp32"},
            findings=[{"fid": "F-1", "category": "code", "rule_id": "strcpy", "severity": "high"}],
            summary={"components": 1, "sbom_coverage": 100.0},
            policy_result={"profile": "lab", "decision": "REVIEW_REQUIRED", "triggered_rules": []},
            llm_client=mock_client,
        )
        self.assertEqual(res["status"], "ai_unavailable")
        self.assertIsNone(res["recommended_decision"])


class TestSecurityGateAndEndpoints(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.ota_security_assessment_service.SECURITY_GATE_MODE", "enforce")
    @patch("app.services.ota_security_assessment_service.db")
    async def test_gate_enforce_blocks_unapproved_and_allows_approved(self, mock_db):
        mock_db.ota_security_assessments.find_one = AsyncMock(return_value={
            "_id": ObjectId(),
            "target_version": "v1.2.3",
            "platform_type": "esp32",
            "target_hash": "abc",
            "status": "completed",
            "final_decision": "REVIEW_REQUIRED",
            "workflow_state": "awaiting_review",
            "policy_result": {"triggered_rules": [{"rule_id": "HIGH_SAST_FINDING"}]},
        })
        with self.assertRaises(HTTPException) as ctx:
            await SecurityGate.check("v1.2.3", "esp32", "abc")
        self.assertEqual(ctx.exception.status_code, 409)

        # Now approved
        mock_db.ota_security_assessments.find_one = AsyncMock(return_value={
            "_id": ObjectId(),
            "target_version": "v1.2.3",
            "platform_type": "esp32",
            "target_hash": "abc",
            "status": "completed",
            "final_decision": "PASS",
            "workflow_state": "approved",
        })
        res = await SecurityGate.check("v1.2.3", "esp32", "abc")
        self.assertTrue(res["allowed"])

    @patch("app.services.ota_security_assessment_service.SECURITY_GATE_MODE", "enforce")
    @patch("app.services.ota_security_assessment_service.db")
    async def test_gate_detects_hash_mismatch(self, mock_db):
        mock_db.ota_security_assessments.find_one = AsyncMock(return_value={
            "_id": ObjectId(),
            "target_version": "v1.2.3",
            "platform_type": "esp32",
            "target_hash": "old_hash",
            "status": "completed",
            "final_decision": "PASS",
            "workflow_state": "auto_passed",
        })
        with self.assertRaises(HTTPException) as ctx:
            await SecurityGate.check("v1.2.3", "esp32", "new_hash")
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail["decision"], "HASH_MISMATCH")

    @patch("app.services.ota_security_assessment_service.create_fix_issue")
    @patch("app.services.ota_security_assessment_service.db")
    async def test_review_request_fix_creates_github_issue(self, mock_db, mock_gh_issue):
        aid = ObjectId()
        base_doc = {
            "_id": aid,
            "target_version": "v1.2.3",
            "platform_type": "esp32",
            "target_hash": "abc",
            "release_ids": [],
            "source": {"repo": "0d3ng/firmware-ota-rolling-key", "git_commit": "deadbeef"},
            "status": "completed",
            "workflow_state": "awaiting_review",
            "evidence": {},
            "findings": [{"fid": "F-1", "severity": "high", "title": "Unsafe strcpy", "rule_id": "strcpy"}],
            "summary": {},
            "policy_result": {"profile": "lab", "decision": "REVIEW_REQUIRED"},
            "final_decision": "REVIEW_REQUIRED",
            "decision_source": "policy",
            "review_history": [],
        }
        updated_doc = {
            **base_doc,
            "workflow_state": "fix_requested",
            "github_issue_number": 42,
            "github_issue_url": "https://github.com/0d3ng/firmware-ota-rolling-key/issues/42",
        }
        mock_db.ota_security_assessments.find_one = AsyncMock(side_effect=[base_doc, updated_doc])
        mock_db.ota_security_assessments.update_one = AsyncMock()
        mock_db.ota_firmware_releases.update_many = AsyncMock()
        mock_gh_issue.return_value = {
            "created": True,
            "number": 42,
            "url": "https://github.com/0d3ng/firmware-ota-rolling-key/issues/42",
        }

        res = await SecurityAssessmentService.review_assessment(
            assessment_id=str(aid),
            review_req=AssessmentReviewRequest(
                action="request_fix",
                reason="Please replace strcpy with strlcpy",
                selected_fids=["F-1"],
                create_github_issue=True,
                ai_rating=5,
            ),
            reviewer_username="lepen",
            reviewer_id="u1",
        )
        self.assertEqual(res.workflow_state, "fix_requested")
        self.assertEqual(res.github_issue_number, 42)
        mock_gh_issue.assert_awaited_once()

    def test_security_endpoints_auth(self):
        resp = client.post("/api/v1/security-assessments", data={"metadata": "{}"}, headers={"Authorization": "Bearer invalid"})
        self.assertEqual(resp.status_code, 401)
        resp2 = client.get("/api/v1/security-assessments", headers={"Authorization": "Bearer invalid"})
        self.assertEqual(resp2.status_code, 401)


if __name__ == "__main__":
    unittest.main()

