from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class UpdateSession(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    session_id: Any
    type: str  # delta | rotation | full
    platform_type: Optional[str] = None
    target_version: Optional[str] = None
    firmware_release_id: Optional[str] = None
    rotation_request_id: Optional[str] = None
    target_edge_ota_id: str
    target_device_ids: Optional[list[str]] = None
    status: str = "preparing"  # preparing | broadcasting | completed | failed | pending
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
