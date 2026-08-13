import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Header, Query
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.firmware_release_schema import FirmwareReleaseResponse, FirmwareReleaseCreate, LatestFirmwareReleaseResponse
from app.services.firmware_release_service import FirmwareReleaseService
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


@router.get("/firmware-releases/", response_model=List[FirmwareReleaseResponse])
async def read_firmware_releases(token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await FirmwareReleaseService.get_all_releases()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/firmware-releases/latest", response_model=LatestFirmwareReleaseResponse)
async def read_latest_firmware_release(
    type: Optional[str] = Query(None),
    authorization: str = Header(...)
):
    try:
        token_type, _, token_str = authorization.partition(" ")
        if token_type.lower() != "bearer" or token_str != SEMAR_API_TOKEN:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid CI/CD token")

        return await FirmwareReleaseService.get_latest_release(release_type=type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/firmware-releases/{release_id}", response_model=FirmwareReleaseResponse)

async def read_firmware_release(release_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await FirmwareReleaseService.get_release(release_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/firmware-releases/", response_model=FirmwareReleaseResponse)
async def create_firmware_release(
    manifest: str = Form(...),
    file: Optional[UploadFile] = File(None),
    token: str = Depends(oauth2_scheme)
):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        try:
            manifest_dict = json.loads(manifest)
            release_data = FirmwareReleaseCreate(**manifest_dict)
        except Exception as json_err:
            raise HTTPException(status_code=400, detail=f"Invalid manifest JSON: {json_err}")

        return await FirmwareReleaseService.create_release(
            release_data=release_data,
            file=file,
            user_id=token_data.user_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
