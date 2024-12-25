#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 23:14:58
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 23:14:58
#  File: project_schema.py
#  Description:
#  """
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.custom_fields import PydanticObjectId


class ProjectCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    user_id: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

class ProjectResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    name: str
    description: Optional[str] = None
    user_id: str
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)