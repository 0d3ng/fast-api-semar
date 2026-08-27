from datetime import datetime
from typing import Optional

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class EdgeOtaCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    multicast_group: Optional[str] = None
    multicast_port: Optional[int] = None
    ttl: Optional[int] = None
    chunk_size: Optional[int] = None
    project_id: str
    active: Optional[bool] = Field(default=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EdgeOtaResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    code: str
    name: str
    ip_address: Optional[str] = None
    multicast_group: Optional[str] = None
    multicast_port: Optional[int] = None
    ttl: Optional[int] = None
    chunk_size: Optional[int] = None
    description: Optional[str] = None
    last_seen_at: Optional[str] = None
    status: Optional[str] = "offline"
    project_id: str
    active: bool
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('inserted_at', 'updated_at', 'deleted_at', 'last_seen_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
