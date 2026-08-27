from datetime import datetime
from typing import Optional

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class EndDeviceCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    platform_type: str
    edge_ota_id: str
    current_firmware_version: Optional[str] = None
    current_key_generation: Optional[int] = 1
    status: Optional[str] = "active"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EndDeviceResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    code: str
    name: str
    description: Optional[str] = None
    platform_type: str
    edge_ota_id: str
    current_firmware_version: Optional[str] = None
    current_key_generation: Optional[int] = 1
    status: Optional[str] = "active"
    last_update_at: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('inserted_at', 'updated_at', 'deleted_at', 'last_update_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
