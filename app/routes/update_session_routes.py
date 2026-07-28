from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.session_ack_schema import SessionAckCreate, SessionAckResponse
from app.schemas.update_session_schema import UpdateSessionCreate, UpdateSessionResponse
from app.services.update_session_service import UpdateSessionService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/update-sessions/{session_id}", response_model=UpdateSessionResponse)
async def read_update_session(session_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.get_session(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/update-sessions/", response_model=UpdateSessionResponse)
async def create_update_session(session_data: UpdateSessionCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.create_session(session_data, token_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/update-sessions/{session_id}/acks", response_model=SessionAckResponse)
async def create_session_ack(session_id: str, ack_data: SessionAckCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await UpdateSessionService.add_session_ack(session_id, ack_data, token_data.user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
