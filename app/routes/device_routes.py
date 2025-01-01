from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.device_schema import DeviceResponse, DeviceCreateUpdate
from app.services.device_service import DeviceService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.post("/devices/", response_model=DeviceResponse)
async def create_device(device: DeviceCreateUpdate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await DeviceService.create_device(device, token_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def read_device(device_id: str, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await DeviceService.get_device(device_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/devices/", response_model=List[DeviceResponse])
async def read_devices(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get devices")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await DeviceService.get_all_devices(token_data.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: str, device: DeviceCreateUpdate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated_user = await DeviceService.update_device(device_id, device, token_data.user_id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return updated_user


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await DeviceService.delete_device(device_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"msg": "Device deleted successfully"}
