from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette import status

from app.middlewares.auth import verify_token
from app.schemas.edge_schema import EdgeResponse, EdgeCreateUpdate
from app.services.edge_service import EdgeService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                      detail="Could not validate credentials",
                                      headers={"WWW-Authenticate": "Bearer"})


@router.post("/edges/", response_model=EdgeResponse)
async def create_edge(edge: EdgeCreateUpdate, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeService.create_edge(edge, token_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/edges/{edge_id}", response_model=EdgeResponse)
async def read_edge(edge_id: str, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeService.get_edge(edge_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/edges/", response_model=List[EdgeResponse])
async def read_edges(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get edges")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await EdgeService.get_all_edges(token_data.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/edges/{edge_id}", response_model=EdgeResponse)
async def update_edge(edge_id: str, edge: EdgeCreateUpdate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated_user = await EdgeService.update_edge(edge_id, edge, token_data.user_id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    return updated_user


@router.delete("/edges/{edge_id}")
async def delete_edge(edge_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await EdgeService.delete_edge(edge_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    return {"msg": "Edge deleted successfully"}