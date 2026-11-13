from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

import pytz
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.utils.custom_fields import PydanticObjectId


class FindingComponent(BaseModel):
    name: str
    version: Optional[str] = None
    cpe: Optional[str] = None


class FindingLocation(BaseModel):
    file: str
    line: Optional[int] = None


class NormalizedFinding(BaseModel):
    """Unified finding produced by normalizers from SBOM/CVE/SAST/Config evidence."""

    fid: str
    tool: str
    tools: List[str] = Field(default_factory=list)
    category: Literal["dependency_cve", "code", "secret", "config"]
    rule_id: str
    cwe: Optional[str] = None
    cve: Optional[str] = None
    severity: Literal["critical", "high", "medium", "low", "info"] = "medium"
    cvss: Optional[float] = None
    epss: Optional[float] = None
    kev: bool = False
    reachable_hint: Optional[str] = None
    title: str = ""
    description: str = ""
    component: Optional[FindingComponent] = None
    location: Optional[FindingLocation] = None
    snippet: Optional[str] = None


class AiTriageItem(BaseModel):
    fid: str
    relevance: Literal["applicable", "likely_false_positive", "uncertain"]
    fp_likelihood: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str
    evidence_refs: List[str] = Field(default_factory=list)


class AiCorrelationItem(BaseModel):
    title: str
    severity: Literal["critical", "high", "medium", "low"]
    finding_fids: List[str] = Field(default_factory=list)
    attack_scenario: str
    compensating_controls: str = ""


class AiMitigationItem(BaseModel):
    priority: int = Field(default=1, ge=1)
    finding_fids: List[str] = Field(default_factory=list)
    action: str
    target: str = ""


class AiAnalysisOutput(BaseModel):
    """Structured JSON output expected from the local LLM (Ollama)."""

    overall_risk: Literal["low", "medium", "high", "critical"]
    recommended_decision: Literal["PASS", "REVIEW_REQUIRED", "BLOCKED"]
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    triage: List[AiTriageItem] = Field(default_factory=list)
    correlations: List[AiCorrelationItem] = Field(default_factory=list)
    mitigations: List[AiMitigationItem] = Field(default_factory=list)
    summary: str


class AssessmentSourceMetadata(BaseModel):
    target_version: str
    platform_type: str = "esp32"
    target_hash: str
    repo: Optional[str] = None
    git_commit: Optional[str] = None
    ci_run_id: Optional[str] = None
    idf_version: Optional[str] = None
    ota_protocol: Optional[str] = None
    sdkconfig_flags: Dict[str, Any] = Field(default_factory=dict)
    tool_versions: Dict[str, str] = Field(default_factory=dict)


class AssessmentReviewRequest(BaseModel):
    action: Literal["approve", "request_fix", "block"]
    reason: str = Field(..., min_length=3, max_length=2000)
    selected_fids: List[str] = Field(default_factory=list)
    create_github_issue: bool = True
    auto_broadcast: bool = False
    ai_rating: Optional[int] = Field(default=None, ge=1, le=5)
    false_positive_fids: List[str] = Field(default_factory=list)


class AssessmentReanalyzeRequest(BaseModel):
    profile: Optional[Literal["lab", "production"]] = None
    model: Optional[str] = None
    run_ai: bool = True


def _serialize_dt(v: Any) -> Any:
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = pytz.UTC.localize(v)
        return v.isoformat()
    return v


class SecurityAssessmentResponse(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    target_version: str
    platform_type: str
    target_hash: str
    release_ids: List[str] = Field(default_factory=list)
    source: Dict[str, Any] = Field(default_factory=dict)
    status: str
    workflow_state: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    policy_result: Dict[str, Any] = Field(default_factory=dict)
    ai_result: Optional[Dict[str, Any]] = None
    diff_vs_previous: Optional[Dict[str, Any]] = None
    final_decision: str
    decision_source: str
    review_history: List[Dict[str, Any]] = Field(default_factory=list)
    github_issue_number: Optional[int] = None
    github_issue_url: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    error_message: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

    @field_validator("inserted_at", "updated_at", mode="before")
    @classmethod
    def convert_datetime(cls, v):
        return _serialize_dt(v)

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

