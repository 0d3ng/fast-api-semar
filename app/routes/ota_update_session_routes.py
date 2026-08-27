from app.schemas.ota_telemetry_schema import OtaTelemetryResponse
from app.services.ota_telemetry_service import OtaTelemetryService
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from starlette import status as http_status

from app.middlewares.auth import verify_token
from app.schemas.ota_session_ack_schema import SessionAckCreate, SessionAckResponse
from app.schemas.ota_update_session_schema import (
    UpdateSessionCreate,
    UpdateSessionResponse,
    UpdateSessionStatusUpdate,
    PendingSessionsResponse,
)
from app.services.ota_update_session_service import UpdateSessionService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(
    status_code=http_status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


@router.get("/update-sessions/", response_model=List[UpdateSessionResponse])
async def read_update_sessions(token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.get_all_sessions()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/update-sessions/pending", response_model=PendingSessionsResponse)
async def get_pending_update_sessions(
    edge_id: str = Query(..., description="ID or Code of Edge OTA"),
    target_version: str = Query(..., description="Target firmware version"),
    token: str = Depends(oauth2_scheme)
):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.get_pending_sessions(edge_id=edge_id, target_version=target_version)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/update-sessions/{session_id}", response_model=UpdateSessionResponse)
async def read_update_session(session_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.get_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/update-sessions/", response_model=UpdateSessionResponse)
async def create_update_session(session_data: UpdateSessionCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.create_session(session_data, token_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/update-sessions/{session_id}/status", response_model=UpdateSessionResponse)
@router.patch("/update-sessions/{session_id}/status", response_model=UpdateSessionResponse)
@router.put("/update-sessions/{session_id}", response_model=UpdateSessionResponse)
@router.patch("/update-sessions/{session_id}", response_model=UpdateSessionResponse)
async def update_session_status(
    session_id: str,
    status_data: UpdateSessionStatusUpdate,
    token: str = Depends(oauth2_scheme)
):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.update_session_status(session_id, status_data.status, token_data.user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/update-sessions/{session_id}/acks", response_model=SessionAckResponse)
async def create_session_ack(session_id: str, ack_data: SessionAckCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.add_session_ack(session_id, ack_data, token_data.user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/update-sessions/{session_id}/telemetries", response_model=List[OtaTelemetryResponse])
@router.get("/update-sessions/{session_id}/telemetry", response_model=List[OtaTelemetryResponse])
async def get_session_telemetry(session_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await OtaTelemetryService.get_telemetry_by_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

