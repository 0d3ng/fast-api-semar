#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 23:26:29
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 23:26:29
#  File: project_routes.py
#  Description:
#  """
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

from app.middlewares.auth import verify_token
from app.schemas.project_schema import ProjectResponse, ProjectCreateUpdate
from app.services.project_service import ProjectService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

@router.post("/projects/", response_model=ProjectResponse)
async def create_project(project: ProjectCreateUpdate, token: str = Depends(oauth2_scheme)):
    try:
        token_data=verify_token(token=token,credentials_exception=credentials_exception)
        return await ProjectService.create_project(project, token_data.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def read_project(project_id: str, token: str = Depends(oauth2_scheme)):
    try:
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await ProjectService.get_project(project_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/projects/", response_model=List[ProjectResponse])
async def read_projects(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("get projects")
        token_data = verify_token(token=token, credentials_exception=credentials_exception)
        return await ProjectService.get_all_projects(token_data.user_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectCreateUpdate, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    updated_user = await ProjectService.update_project(project_id, project, token_data.user_id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return updated_user

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token=token, credentials_exception=credentials_exception)
    success = await ProjectService.delete_project(project_id, token_data.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return {"msg": "Project deleted successfully"}