#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-01-07 14:33:46
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-01-07 14:33:46
#   File: server_routes.py
#   Description:
#   """
from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.sensor_actuator_schema import SensorActuatorResponse
from app.services.server_service import ServerService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.get("/servers/{protocol}", response_model=SensorActuatorResponse)
async def get_server(protocol: str, environment: str = Query(...), token: str = Depends(oauth2_scheme)):
    try:
        logger.info(f"get server: {protocol} {environment}")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await ServerService.get_server_config(protocol=protocol, environment=environment)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
