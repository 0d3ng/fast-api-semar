#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:50:59
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 22:50:59
#  File: project.py
#  Description:
#  """
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class Project(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    name: str
    description: str  # Rename to align with the hashed password used in the script
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)