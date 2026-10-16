from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.ota_config_update_request_schema import (
    ConfigUpdateRequestCreate,
    ConfigUpdateRequestResponse,
    ConfigUpdateAckPayload,
)
from app.services.ota_config_update_request_service import ConfigUpdateRequestService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


@router.get("/config-update-requests", response_model=List[ConfigUpdateRequestResponse])
async def read_config_update_requests(token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await ConfigUpdateRequestService.get_all_requests()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/config-update-requests/{request_id}", response_model=ConfigUpdateRequestResponse)
async def read_config_update_request(request_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await ConfigUpdateRequestService.get_request_by_id(request_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/config-update-requests", response_model=ConfigUpdateRequestResponse)
async def create_config_update_request(req_data: ConfigUpdateRequestCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await ConfigUpdateRequestService.create_config_request(req_data, token_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/config-update-requests/{request_id}/ack", response_model=ConfigUpdateRequestResponse)
async def ack_config_update_request(request_id: str, ack_data: ConfigUpdateAckPayload):
    # Unsecured or token-free so Edge Gateway / End Device can post ACKs directly
    try:
        return await ConfigUpdateRequestService.record_device_ack(request_id, ack_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
