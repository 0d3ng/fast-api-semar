#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-01-07 12:01:16
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-01-07 12:01:16
#   File: server.py
#   Description:
#   """
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Server(BaseModel):
    name: str
    environment: str
    protocol: str
    host: str
    port: int
    parameters: dict
    inserted_by: Optional[str] = None
    inserted_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
