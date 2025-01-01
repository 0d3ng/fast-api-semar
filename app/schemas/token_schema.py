#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:46:30
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-11-28 19:02:06
#  File: token_schema.py
#  Description:
#  """
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class TokenCreate(BaseModel):
    device_id: str
    name: str
    description: Optional[str] = None
    expires_at: datetime


class TokenResponse(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    device_id: str
    device_name: str
    name: str
    token: str
    description: Optional[str] = None
    expires_at: datetime
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TokenLogin(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str | None = None
    username: str | None = None


class TokenDataDevice(BaseModel):
    user_id: str
    device_id: str
    username: Optional[str] = None
    device_code: str
