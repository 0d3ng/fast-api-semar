from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.middlewares.auth import verify_token
from app.schemas.user_schema import Token
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.utils.logger import logger

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

@router.post("/login/", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"username: {form_data.username} password: {form_data.password}")
    user = await UserService.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials",headers={"WWW-Authenticate": "Bearer"})
    return await UserService.create_access_token(user)

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, token: str = Depends(oauth2_scheme)):
    token_data=verify_token(token=token,credentials_exception=credentials_exception)
    return await UserService.create_user(user, token_data.user_id)

@router.get("/users/{user_id}", response_model=UserResponse)
async def read_user(user_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.get("/users/", response_model=List[UserResponse])
async def read_users(token: str = Depends(oauth2_scheme)):
    # logger.info("get users")
    # token_data = verify_token(token=token, credentials_exception=credentials_exception)
    # return await UserService.get_all_users()
    try:
        logger.info("get users")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await UserService.get_all_users()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user: UserUpdate,token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated_user = await UserService.update_user(user_id, user, token_data.user_id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await UserService.delete_user(user_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"msg": "User deleted successfully"}

