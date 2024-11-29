from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class User(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id')
    username: str
    email: str
    password: str  # Rename to align with the hashed password used in the script
    name: str
    active: bool
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)