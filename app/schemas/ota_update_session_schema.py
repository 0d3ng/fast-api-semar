from datetime import datetime
from typing import Optional, Literal, Dict, Any, List

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class UpdateSessionCreate(BaseModel):
    session_id: Any
    type: str  # delta | rotation | full
    platform_type: Optional[str] = None
    target_version: Optional[str] = None
    firmware_release_id: Optional[str] = None
    rotation_request_id: Optional[str] = None
    target_edge_ota_id: str
    target_device_ids: Optional[List[str]] = None
    status: Optional[str] = "preparing"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UpdateSessionStatusUpdate(BaseModel):
    status: Literal["downloading", "broadcasting", "completed", "completed_partial", "failed"]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PendingSessionItem(BaseModel):
    session_id: Any
    type: str
    manifest: Dict[str, Any]
    target_device_ids: List[str]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PendingSessionsResponse(BaseModel):
    sessions: List[PendingSessionItem]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UpdateSessionResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    session_id: str
    type: str
    platform_type: Optional[str] = None
    target_version: Optional[str] = None
    firmware_release_id: Optional[str] = None
    rotation_request_id: Optional[str] = None
    target_edge_ota_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('started_at', 'completed_at', 'inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                import pytz
                v = pytz.UTC.localize(v)
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
