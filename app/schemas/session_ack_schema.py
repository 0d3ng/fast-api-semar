from datetime import datetime
from typing import Optional

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class SessionAckCreate(BaseModel):
    end_device_id: str
    status: str  # success | failed
    notes: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SessionAckResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    update_session_id: str
    end_device_id: str
    acked_at: Optional[str] = None
    status: str
    notes: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('acked_at', 'inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
