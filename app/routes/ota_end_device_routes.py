from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.ota_end_device_schema import EndDeviceResponse, EndDeviceCreateUpdate
from app.services.ota_end_device_service import EndDeviceService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


@router.post("/end-devices", response_model=EndDeviceResponse)
async def create_end_device(end_device: EndDeviceCreateUpdate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EndDeviceService.create_end_device(end_device, token_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/end-devices/{end_device_id}", response_model=EndDeviceResponse)
async def read_end_device(end_device_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await EndDeviceService.get_end_device(end_device_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/end-devices/edge-ota/{edge_ota_id}", response_model=EndDeviceResponse)
async def read_end_device_by_edge_ota(edge_ota_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await EndDeviceService.get_end_device_by_edge_ota_id(edge_ota_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



@router.get("/end-devices", response_model=List[EndDeviceResponse])
async def read_end_devices(
    platform_type: Optional[str] = Query(None),
    edge_ota_id: Optional[str] = Query(None),
    outdated: Optional[bool] = Query(None),
    token: str = Depends(oauth2_scheme)
):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EndDeviceService.get_all_end_devices(
            platform_type=platform_type,
            edge_ota_id=edge_ota_id,
            outdated=outdated,
            user_id=token_data.user_id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/end-devices/{end_device_id}", response_model=EndDeviceResponse)
async def update_end_device(end_device_id: str, end_device: EndDeviceCreateUpdate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated = await EndDeviceService.update_end_device(end_device_id, end_device, token_data.user_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EndDevice not found")
    return updated


@router.delete("/end-devices/{end_device_id}")
async def delete_end_device(end_device_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await EndDeviceService.delete_end_device(end_device_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EndDevice not found")
    return {"msg": "EndDevice deleted successfully"}
