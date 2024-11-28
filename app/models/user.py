from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict


class User(BaseModel):
    id: Optional[ObjectId] = Field(alias='_id')
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