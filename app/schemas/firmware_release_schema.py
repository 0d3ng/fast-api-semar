from datetime import datetime
from typing import Optional, Any

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class FirmwareReleaseCreate(BaseModel):
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

    model_config = ConfigDict(arbitrary_types_allowed=True)


class FirmwareReleaseResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
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
    download_url: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)


class LatestFirmwareReleaseResponse(BaseModel):
    target_version: Optional[str] = None
    type: Optional[str] = None
    platform_type: Optional[str] = None
    target_hash: Optional[str] = None
    download_url: Optional[str] = None
    created_at: Optional[str] = None

