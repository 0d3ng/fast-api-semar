from datetime import datetime
from typing import Optional

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class EdgeCreateUpdate(BaseModel):
    name: str
    description: str
    type: str
    protocol: str
    project_id: str
    active: Optional[bool] = Field(default=True)
    config: Optional[dict] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EdgeResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    code: str
    name: str
    description: str
    type: str
    protocol: str
    project_id: str
    active: bool
    config: Optional[dict] = None
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