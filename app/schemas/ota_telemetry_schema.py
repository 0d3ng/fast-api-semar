from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.utils.custom_fields import PydanticObjectId


class OtaTelemetryCreate(BaseModel):
    session_id: str
    device_id: str
    stage: str
    metrics: Dict[str, Any] = {}
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OtaTelemetryResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    session_id: str
    device_id: str
    stage: str
    metrics: Dict[str, Any] = {}
    timestamp: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None

    @field_validator('timestamp', 'inserted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
