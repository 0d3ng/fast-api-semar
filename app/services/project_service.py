#  """
#  Copyright (c) 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 23:14:03
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 23:14:03
#  File: project_service.py
#  Description:
#  """
import traceback
from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pytz import timezone

from app.models.project import Project
from app.schemas.project_schema import ProjectCreateUpdate, ProjectResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
datetime_jpn = datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class ProjectService:
    @staticmethod
    async def create_project(project: ProjectCreateUpdate, current_user: str):
        try:
            logger.info(project)
            new_project: Project = Project(
                name=project.name,
                description=project.description,
                user_id=project.user_id,
                inserted_at=datetime_jpn,
                inserted_by=current_user
            )
            logger.info(new_project)
            new_project_inserted = await db.projects.insert_one(new_project.model_dump(by_alias=True))
            new_user_id = new_project_inserted.inserted_id
            return ProjectResponse(_id=new_user_id,
                                name=project.name,
                                description=project.description,
                                user_id=project.user_id,
                                inserted_at=datetime_jpn,
                                inserted_by=current_user)
        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_project(role_id: str):
        try:
            project = await db.projects.find_one({"_id": ObjectId(role_id)})
            if project:
                return ProjectResponse(**project)
            raise HTTPException(status_code=404, detail="Role not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_projects():
        try:
            projects = []
            cursor = db.projects.find({})
            async for project in cursor:
                logger.info(f"{project} {project["_id"]}")
                project_response = ProjectResponse(**project)
                projects.append(project_response)
                logger.info("")
            return projects
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_project(project_id: str, project_update: ProjectCreateUpdate, current_user: str):
        try:
            update_data = {k: v for k, v in project_update.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            logger.info(update_data)
            result = await db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": update_data})
            logger.info(result)
            if result.matched_count == 1:
                return await ProjectService.get_project(project_id)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_project(project_id: str, current_user: str):
        try:
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            result = await db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))