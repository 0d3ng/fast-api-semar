from datetime import datetime
from typing import Optional, Any

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class RotationRequestCreate(BaseModel):
    trigger_type: str  # scheduled | on_demand
    target_scope: str  # all_edges | specific_edges

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RotationRequestCicdCallback(BaseModel):
    new_key_generation: int
    signed_manifest: Any

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RotationRequestResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    trigger_type: str
    requested_by: str
    target_scope: str
    status: str
    new_key_generation: Optional[int] = None
    signed_manifest: Optional[Any] = None
    requested_at: Optional[str] = None
    signed_at: Optional[str] = None
    broadcast_at: Optional[str] = None
    completed_at: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('requested_at', 'signed_at', 'broadcast_at', 'completed_at', 'inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
