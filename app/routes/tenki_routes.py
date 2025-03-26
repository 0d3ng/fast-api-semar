#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-03-26 15:10:07
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-03-26 15:10:07
#   File: tenki_routes.py
#   Description:
#   """
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.tenki_schema import TenkiCreate, TenkiResponse
from app.services.tenki_services import TenkiServices
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.post("/tenki")
async def create_tenki(data: TenkiCreate, token: str = Depends(oauth2_scheme)):
    try:
        logger.info("create tenki")
        return await TenkiServices.insert(data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tenki/last", response_model=TenkiResponse)
async def get_tenki_last(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get last tenki")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await TenkiServices.get_last_tenki()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
