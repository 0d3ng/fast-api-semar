import os
import traceback
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pytz import timezone

from app.middlewares.auth import verify_password, create_access_token
from app.models.user import User
from app.schemas.user_schema import Token, UserResponse
from app.schemas.user_schema import UserCreate, UserUpdate
from app.utils.db import db, logger
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
datetime_jpn = datetime.now(tz=timezone("Asia/Tokyo")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


class UserService:
    @staticmethod
    async def authenticate_user(username: str, password: str):
        try:
            user = await db.users.find_one({"username": username})
            logger.info(user)
            if user or not verify_password(password, user["password"]):
                return UserResponse(**user)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def create_access_token(user: User):
        try:
            expire = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
            payload = {
                "user_id": str(user.id),
                "username": user.username
            }
            access_token = create_access_token(payload, expires_delta=expire)
            return Token(access_token=access_token, token_type="bearer")
        except Exception as e:
            logger.error(f"failed to create access token: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def create_user(user: UserCreate, current_user: str):
        try:
            hashed_password = pwd_context.hash(user.password)
            new_user = User(
                username=user.username,
                email=user.email,
                hashed_password=hashed_password,
                inserted_at=datetime_jpn,
                updated_by=current_user
            )
            await db.users.insert_one(new_user.model_dump(by_alias=True))
            return new_user
        except Exception as e:
            logger.error(f"failed to create access token: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_user(user_id: str):
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return UserResponse(**user)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_users():
        try:
            users = []
            cursor = db.users.find({})
            async for user in cursor:
                role_ids = db.user_roles.find({"user_id": user["_id"]})
                r_ids=[]
                async for role_id in role_ids:
                    r_ids.append(role_id["role_id"])
                logger.info(r_ids)

                r_names = []
                for r_id in r_ids:
                    logger.info(r_id)
                    role_name = (await db.roles.find_one({"_id": r_id}))["name"]
                    r_names.append(role_name)
                logger.info(r_names)
                user_response = UserResponse(**user, roles=r_names)
                users.append(user_response)
            return users
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_user(user_id: str, user_update: UserUpdate, current_user: str):
        try:
            update_data = {k: v for k, v in user_update.model_dump(exclude_unset=True).items() if v is not None}
            if "password" in update_data:
                update_data["hashed_password"] = pwd_context.hash(update_data.pop("password"))
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return await UserService.get_user(user_id)
            return None
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_user(user_id: str, current_user: str):
        try:
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))