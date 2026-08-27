from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class FirmwareRelease(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    target_version: str
    base_version: Optional[str] = None
    type: str
    platform_type: str
    target_hash: str
    delta_hash: Optional[str] = None
    delta_algorithm: Optional[str] = None
    delta_size: Optional[int] = None
    target_size: int
    key_generation: int
    signature: Any
    file_path: Optional[str] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
