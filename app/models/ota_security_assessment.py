from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class SecurityAssessment(BaseModel):
    """MongoDB model for firmware security assessments (collection: ota_security_assessments)."""

    id: Optional[PydanticObjectId] = Field(alias="_id", default_factory=PydanticObjectId)
    target_version: str
    platform_type: str = "esp32"
    target_hash: str
    release_ids: List[str] = Field(default_factory=list)
    source: Dict[str, Any] = Field(default_factory=dict)
    status: str = "received"  # received | analyzing | completed | error
    workflow_state: str = "awaiting_review"  # auto_passed | awaiting_review | fix_requested | approved | blocked | superseded
    evidence: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    policy_result: Dict[str, Any] = Field(default_factory=dict)
    ai_result: Optional[Dict[str, Any]] = None
    diff_vs_previous: Optional[Dict[str, Any]] = None
    final_decision: str = "REVIEW_REQUIRED"  # PASS | REVIEW_REQUIRED | BLOCKED
    decision_source: str = "policy"  # policy | ai_escalation | human_review
    review_history: List[Dict[str, Any]] = Field(default_factory=list)
    github_issue_number: Optional[int] = None
    github_issue_url: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    error_message: Optional[str] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

