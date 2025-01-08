#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-01-07 12:04:18
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-01-07 12:04:18
#   File: server_schema.py
#   Description:
#   """
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.utils.custom_fields import PydanticObjectId


class ServerResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    name: str
    environment: str
    protocol: str
    host: str
    ports: dict
    parameters: dict
    inserted_by: Optional[str] = None
    inserted_at: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_by: Optional[str] = None
    deleted_at: Optional[str] = None

    @field_validator('inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)
