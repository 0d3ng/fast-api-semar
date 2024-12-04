from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.middlewares.auth import verify_token
from app.schemas.role_schema import RoleResponse, RoleCreateUpdate
from app.services.role_service import RoleService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

@router.post("/roles/", response_model=RoleResponse)
async def create_role(role: RoleCreateUpdate, token: str = Depends(oauth2_scheme)):
    try:
        token_data=verify_token(token=token,credentials_exception=credentials_exception)
        return await RoleService.create_role(role, token_data.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))

@router.get("/roles/{role_id}", response_model=RoleResponse)
async def read_role(role_id: str, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await RoleService.get_role(role_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/roles/", response_model=List[RoleResponse])
async def read_roles(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get roles")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await RoleService.get_all_roles()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(role_id: str, role: RoleCreateUpdate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated_user = await RoleService.update_role(role_id, role, token_data.user_id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user

@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await RoleService.delete_role(role_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"msg": "Role deleted successfully"}

