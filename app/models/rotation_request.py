from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class RotationRequest(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    trigger_type: str  # scheduled | on_demand
    requested_by: str
    target_scope: str  # all_edges | specific_edges
    status: str = "pending_cicd"  # pending_cicd | ready_to_broadcast | broadcasting | completed | failed
    new_key_generation: Optional[int] = None
    signed_manifest: Optional[Any] = None
    requested_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    broadcast_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
