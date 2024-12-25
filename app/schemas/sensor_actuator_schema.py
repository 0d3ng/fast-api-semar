from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.custom_fields import PydanticObjectId


class SensorActuatorCreate(BaseModel):
    device_id: str
    device_code: str
    data: dict
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class SensorActuatorResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    device_id: str
    device_code: str
    data: dict
    timestamp: Optional[datetime] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)