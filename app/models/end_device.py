from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class EndDevice(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    code: str
    name: str
    description: Optional[str] = None
    platform_type: str
    edge_ota_id: str
    current_firmware_version: Optional[str] = None
    current_key_generation: Optional[int] = 1
    status: Optional[str] = "active"
    last_update_at: Optional[datetime] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
