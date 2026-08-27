from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.ota_edge_schema import EdgeOtaResponse, EdgeOtaCreateUpdate
from app.services.ota_edge_service import EdgeOtaService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


@router.post("/edge-otas", response_model=EdgeOtaResponse)
async def create_edge_ota(edge_ota: EdgeOtaCreateUpdate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeOtaService.create_edge_ota(edge_ota, token_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/edge-otas/{edge_ota_id}", response_model=EdgeOtaResponse)
async def read_edge_ota(edge_ota_id: str, token: str = Depends(oauth2_scheme)):
    try:
        verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeOtaService.get_edge_ota(edge_ota_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/edge-otas", response_model=List[EdgeOtaResponse])
async def read_edge_otas(token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeOtaService.get_all_edge_otas(token_data.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/edge-otas/{edge_ota_id}", response_model=EdgeOtaResponse)
async def update_edge_ota(edge_ota_id: str, edge_ota: EdgeOtaCreateUpdate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated = await EdgeOtaService.update_edge_ota(edge_ota_id, edge_ota, token_data.user_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EdgeOta not found")
    return updated


@router.delete("/edge-otas/{edge_ota_id}")
async def delete_edge_ota(edge_ota_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await EdgeOtaService.delete_edge_ota(edge_ota_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EdgeOta not found")
    return {"msg": "EdgeOta deleted successfully"}
