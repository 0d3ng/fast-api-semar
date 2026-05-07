#   """
#   Copyright (c) 2026 lepen - All Rights Reserved
#   Created by lepen on 2026-05-07 14:32:50
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2026-05-07 14:32:49
#   File: edge_data_schema.py
#   Description:
#   """
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.custom_fields import PydanticObjectId


class EdgeDataCreate(BaseModel):
    edge_id: Optional[str] = None
    data: dict
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EdgeDataResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    edge_id: str
    data: dict
    timestamp: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @field_validator('timestamp', 'inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)