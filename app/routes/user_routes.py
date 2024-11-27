from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.middlewares.auth import get_current_user
from app.schemas.user_schema import Token
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter()

@router.post("/login/", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await UserService.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return await UserService.create_access_token(user)

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, current_user: str = Depends(get_current_user)):
    return await UserService.create_user(user, current_user)

@router.get("/users/{user_id}", response_model=UserResponse)
async def read_user(user_id: str):
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users/", response_model=List[UserResponse])
async def read_users():
    return await UserService.get_all_users()

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user: UserUpdate, current_user: str = Depends(get_current_user)):
    updated_user = await UserService.update_user(user_id, user, current_user)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: str = Depends(get_current_user)):
    success = await UserService.delete_user(user_id, current_user)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"msg": "User deleted successfully"}

