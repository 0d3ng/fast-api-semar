from typing import List

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.ota_rotation_request_schema import (
    RotationRequestCicdCallback,
    RotationRequestCreate,
    RotationRequestResponse,
    CurrentKeyGenerationResponse,
)
from app.services.ota_rotation_request_service import RotationRequestService
from app.utils.config import SEMAR_API_TOKEN
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


@router.get("/rotation-requests/", response_model=List[RotationRequestResponse])
async def read_rotation_requests(token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await RotationRequestService.get_all_rotation_requests()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/rotation-requests/{rotation_id}", response_model=RotationRequestResponse)
async def read_rotation_request(rotation_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await RotationRequestService.get_rotation_request(rotation_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/rotation-requests/", response_model=RotationRequestResponse)
async def create_rotation_request(req_data: RotationRequestCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await RotationRequestService.create_rotation_request(req_data, token_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/rotation-requests/{rotation_id}/broadcast", response_model=RotationRequestResponse)
async def broadcast_rotation_request(rotation_id: str, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await RotationRequestService.broadcast_rotation(rotation_id, token_data.user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/rotation-requests/{rotation_id}/cicd-callback", response_model=RotationRequestResponse)
async def cicd_callback(
    rotation_id: str,
    callback_data: RotationRequestCicdCallback,
    authorization: str = Header(...)
):
    try:
        # Validate SEMAR_API_TOKEN
        token_type, _, token_str = authorization.partition(" ")
        if token_type.lower() != "bearer" or token_str != SEMAR_API_TOKEN:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid CI/CD token")

        return await RotationRequestService.handle_cicd_callback(rotation_id, callback_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/key-generation/current", response_model=CurrentKeyGenerationResponse)
async def get_current_key_generation(authorization: str = Header(...)):
    try:
        token_type, _, token_str = authorization.partition(" ")
        if token_type.lower() != "bearer" or token_str != SEMAR_API_TOKEN:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid CI/CD token")

        return await RotationRequestService.get_current_key_generation()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

