from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class EdgeOta(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    code: str
    name: str
    ip_address: Optional[str] = None
    multicast_group: Optional[str] = None
    multicast_port: Optional[int] = None
    description: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    status: Optional[str] = "offline"
    project_id: str
    active: Optional[bool] = Field(default=True)
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
