import json
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Header, Query
from fastapi.security import OAuth2PasswordBearer
from starlette import status
from starlette.responses import FileResponse

from app.middlewares.auth import verify_token
from app.schemas.firmware_release_schema import FirmwareReleaseResponse, FirmwareReleaseCreate, LatestFirmwareReleaseResponse
from app.services.firmware_release_service import FirmwareReleaseService
from app.utils.config import SEMAR_API_TOKEN, FIRMWARE_FOLDER
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
    platform_type: Optional[str] = Query(None),
    authorization: str = Header(...)
):
    try:
        token_type, _, token_str = authorization.partition(" ")
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
            
        if token_str != SEMAR_API_TOKEN:
            try:
                verify_token(token=token_str, credentials_exception=credentials_exception)
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid CI/CD or JWT token")

        return await FirmwareReleaseService.get_latest_release(release_type=type, platform_type=platform_type)
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


@router.post("/firmware-releases", response_model=FirmwareReleaseResponse)
async def create_firmware_release(
    manifest: str = Form(...),
    file: Optional[UploadFile] = File(None),
    authorization: str = Header(...)
):
    try:
        token_type, _, token_str = authorization.partition(" ")
        if token_type.lower() != "bearer" or token_str != SEMAR_API_TOKEN:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid CI/CD token")

        try:
            manifest_dict = json.loads(manifest)
            release_data = FirmwareReleaseCreate(**manifest_dict)
        except Exception as json_err:
            raise HTTPException(status_code=400, detail=f"Invalid manifest JSON: {json_err}")

        return await FirmwareReleaseService.create_release(
            release_data=release_data,
            file=file,
            user_id="system"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/firmware-releases/download/{filename}")
async def download_firmware_release_file(filename: str):
    file_path = os.path.join(FIRMWARE_FOLDER, "ota", filename)
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type='application/octet-stream',
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    raise HTTPException(status_code=404, detail="File not found")
