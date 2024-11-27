from pydantic import BaseModel, Field, BaseConfig
from typing import Optional
from bson import ObjectId

class User(BaseModel):
    id: Optional[ObjectId] = Field(alias='_id')
    username: str
    email: str
    hashed_password: str  # Rename to align with the hashed password used in the script
    name: str
    role: str
    active: bool
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str  # Ensures ObjectId is serialized correctly
        }