#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:42:32
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Date: 2024-12-04 22:37:38
#  File: role.py
#  Description:
#  """
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.utils.custom_fields import PydanticObjectId


class Role(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    name: str
    description: Optional[str] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
