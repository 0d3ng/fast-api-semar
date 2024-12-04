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
from app.utils.db import db
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
            logger.info(user)
            new_user: User = User(
                username=user.username,
                email=user.email,
                password=hashed_password,
                name=user.name,
                inserted_at=datetime_jpn,
                inserted_by=current_user
            )
            logger.info(new_user)
            new_user_inserted = await db.users.insert_one(new_user.model_dump(by_alias=True))
            new_user_id = new_user_inserted.inserted_id
            user_roles = [{"user_id": new_user_id, "role_id": ObjectId(role_id)} for role_id in user.roles]
            logger.info(user_roles)
            if user_roles:
                await db.user_roles.insert_many(user_roles)

            r_names = []
            for r_id in user_roles:
                logger.info(f"{r_id} {type(r_id)}")
                role_name = await db.roles.find_one({"_id": r_id["role_id"]})
                logger.info(role_name)
                r_names.append(role_name["name"])
            logger.info(r_names)
            return UserResponse(_id=new_user_id,
                                username=user.username,
                                email=user.email,
                                name=user.name,
                                roles=r_names,
                                active=True,
                                inserted_at=datetime_jpn,
                                inserted_by=current_user)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_user(user_id: str):
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                role_ids = db.user_roles.find({"user_id": user["_id"]})
                r_ids = []
                async for role_id in role_ids:
                    r_ids.append(role_id["role_id"])
                logger.info(r_ids)

                r_names = []
                for r_id in r_ids:
                    logger.info(f"{r_id} {type(r_id)}")
                    role_name = (await db.roles.find_one({"_id": r_id}))["name"]
                    r_names.append(role_name)
                logger.info(r_names)
                return UserResponse(**user, roles=r_names)
            raise HTTPException(status_code=404, detail="User not found")
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
                logger.info(f"{user} {user["_id"]}")
                role_ids = db.user_roles.find({"user_id": user["_id"]})
                r_ids = []
                async for role_id in role_ids:
                    r_ids.append(role_id["role_id"])
                logger.info(r_ids)

                r_names = []
                for r_id in r_ids:
                    logger.info(f"{r_id} {type(r_id)}")
                    role_name = (await db.roles.find_one({"_id": r_id}))["name"]
                    logger.info(f"{role_name} {type(role_name)}")
                    r_names.append(role_name)
                logger.info(r_names)
                user_response = UserResponse(**user, roles=r_names)
                users.append(user_response)
                logger.info("")
            return users
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_user(user_id: str, user_update: UserUpdate, current_user: str):
        try:
            update_data = {k: v for k, v in user_update.model_dump(exclude_unset=True).items() if v is not None}
            logger.info(update_data)
            if "password" in update_data:
                update_data["password"] = pwd_context.hash(update_data.pop("password"))
            roles = update_data["roles"]
            update_data.pop("roles", None)
            update_data["updated_at"] = datetime_jpn
            update_data["updated_by"] = current_user
            logger.info(update_data)
            result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 1:
                roles_update = []
                logger.info(roles)
                for role in roles:
                    roles_update.append({"user_id": ObjectId(user_id), "role_id": ObjectId(role)})
                if roles_update:
                    logger.info(roles_update)
                    await db.user_roles.delete_many({"user_id": ObjectId(user_id)})  # for update the user roles
                    result_inserted = await db.user_roles.insert_many(roles_update)
                    logger.info(f"{result_inserted}")
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
