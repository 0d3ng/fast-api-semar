#   """
#   Copyright (c) 2026 lepen - All Rights Reserved
#   Created by lepen on 2026-05-07 14:50:49
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2026-05-07 14:50:49
#   File: edge_data_routes.py
#   Description:
#   """
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.edge_data_schema import EdgeDataResponse, EdgeDataCreate
from app.services.edge_data_service import EdgeDataService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.post("/edge_data", response_model=EdgeDataResponse)
async def create(sensor_data: EdgeDataCreate, token: str = Depends(oauth2_scheme)):
    try:
        # logger.info(f"create data: {sensor_data} with token: {token}")
        token_data = verify_token(token=token, credentials_exception=credentials_exception, is_device=True)
        return await EdgeDataService.create_edge_data(sensor_data, token_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/edge_data/{edge_code}", response_model=List[EdgeDataResponse])
async def read_edge_data(edge_code: str, token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get devices")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeDataService.get_edge_all_data(edge_code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/edge_data/{edge_code}/last", response_model=EdgeDataResponse)
async def read_edge_data(edge_code: str, token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get devices")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeDataService.get_edge_last_data(edge_code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
