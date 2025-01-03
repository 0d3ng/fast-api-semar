from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.custom_fields import PydanticObjectId


class SensorActuatorCreate(BaseModel):
    device_id: Optional[str] = None
    device_code: Optional[str] = None
    data: dict
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SensorActuatorResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    device_id: str
    device_code: str
    data: dict
    timestamp: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('timestamp', 'inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
