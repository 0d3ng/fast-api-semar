from typing import Optional, List

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    name: str
    roles: Optional[List[ObjectId]] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    roles: Optional[List[ObjectId]] = None
    active: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserResponse(BaseModel):
    id: ObjectId = Field(
        alias="_id",
        description="Unique identifier in mongo db"
    )
    username: str
    email: str
    name: str
    roles: Optional[List[str]] = []
    active: bool

    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
