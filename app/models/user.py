#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:45:30
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 07:11:19
#  File: user.py
#  Description:
#  """

from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, EmailStr

from app.utils.custom_fields import PydanticObjectId


class User(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id',default_factory=PydanticObjectId)
    username: str
    email: EmailStr
    password: str  # Rename to align with the hashed password used in the script
    name: str
    active: Optional[bool] = True
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)