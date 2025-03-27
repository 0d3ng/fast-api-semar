#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-03-26 14:55:14
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-03-26 14:55:14
#   File: tenki_schema.py
#   Description:
#   """
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TenkiCreate(BaseModel):
    date_pollen: datetime
    pollen: str
    weather: str
    temperature_high: int
    temperature_low: int
    precipitation: int

    model_config = ConfigDict(arbitrary_types_allowed=True)

class TenkiResponse(BaseModel):
    date_pollen: datetime
    pollen: str
    weather: str
    temperature_high: int
    temperature_low: int
    precipitation: int
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    @field_validator('inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)