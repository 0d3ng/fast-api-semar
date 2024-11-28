from bson import ObjectId
from pydantic import BaseModel
from typing import Optional, List


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    name: str
    roles: Optional[List[ObjectId]]=[]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str  # Ensures ObjectId is serialized correctly
        }

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    roles: Optional[List[ObjectId]] = None
    active: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str  # Ensures ObjectId is serialized correctly
        }

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    name: str
    roles: Optional[List[ObjectId]]
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

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str