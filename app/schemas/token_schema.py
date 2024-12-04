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

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: str | None = None
    username: str | None = None