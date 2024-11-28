from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId

class Role(BaseModel):
    id: Optional[ObjectId] = Field(alias='_id')
    name: str
    description: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
