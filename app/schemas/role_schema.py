from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.custom_fields import PydanticObjectId


class RoleCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class RoleResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    name: str
    description: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)