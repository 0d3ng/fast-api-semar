#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-01 19:04:30
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-01 19:04:30
#  File: widget_routes.py
#  Description:
#  """
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.widget_schema import WidgetResponse
from app.services.widget_service import WidgetService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.get("/widgets/", response_model=List[WidgetResponse])
async def read_widgets(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get tokens")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await WidgetService.get_all_widgets(token_data.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
