#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-01-20 16:13:38
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-01-20 16:13:38
#   File: amedas_routes.py
#   Description:
#   """
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.schemas.amedas_schema import AmedasCreate, AmedasResponse
from app.services.amedas_service import AmedasService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.post("/amedas")
async def create_amedas(data: List[AmedasCreate], token: str = Depends(oauth2_scheme)):
    try:
        logger.info("create bulk amedas")
        documents = [item.model_dump() for item in data]
        return await AmedasService.insert(documents)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/amedas", response_model=AmedasResponse)
async def get_amedas_last(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get last amedas")
        return await AmedasService.get_sensor_data_latest()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
