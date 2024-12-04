#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:46:35
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 21:05:08
#  File: user_schema.py
#  Description:
#  """

from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, EmailStr

from app.utils.custom_fields import PydanticObjectId


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    name: str
    roles: Optional[List[str]] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    roles: Optional[List[str]] = None
    active: Optional[bool] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UserResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
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
