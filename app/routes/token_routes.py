from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.token_schema import TokenResponse, TokenCreate
from app.services.token_service import TokenService
from app.services.user_service import UserService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.post("/tokens/", response_model=TokenResponse)
async def create_device(token_create: TokenCreate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token_create, credentials_exception=credentials_exception)
        user = await UserService.get_user(token_data.user_id)
        if user:
            return await TokenService.create_token(token_create, user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tokens/{device_id}", response_model=TokenResponse)
async def read_device(device_id: str, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await TokenService.get_device(device_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/tokens/", response_model=List[TokenResponse])
async def read_devices(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get roles")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await TokenService.get_all_devices()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/tokens/{device_id}", response_model=TokenResponse)
async def update_device(device_id: str, device: DeviceCreateUpdate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated_user = await TokenService.update_device(device_id, device, token_data.user_id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return updated_user


@router.delete("/tokens/{device_id}")
async def delete_device(device_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await TokenService.delete_device(device_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"msg": "Device deleted successfully"}
