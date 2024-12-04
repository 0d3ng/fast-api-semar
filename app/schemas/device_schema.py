#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-05 00:35:44
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-05 00:35:44
#  File: device_schema.py
#  Description:
#  """
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.custom_fields import PydanticObjectId


class DeviceCreateUpdate(BaseModel):
    name: str
    type: str
    protocol: str
    project_id: str
    active: Optional[bool] = Field(default=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DeviceResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    code: str
    name: str
    type: str
    protocol: str
    project_id: str
    active: bool
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
