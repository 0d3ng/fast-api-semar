from datetime import datetime
from typing import Optional

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class UpdateSessionCreate(BaseModel):
    session_id: str
    type: str  # delta | rotation
    firmware_release_id: Optional[str] = None
    rotation_request_id: Optional[str] = None
    target_edge_ota_id: str
    status: Optional[str] = "preparing"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UpdateSessionResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    session_id: str
    type: str
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
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
