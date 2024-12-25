#   """
#   Copyright (c) 2024 lepen - All Rights Reserved
#   Created by lepen on 2024-12-06 21:35:02
#  #
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2024-12-06 21:08:07
#   File: token_service.py
#   Description:
#   """

import traceback
from datetime import datetime, timedelta

import pytz
from bson import ObjectId
from fastapi import HTTPException
from passlib.context import CryptContext
from pytz import timezone

from app.middlewares.auth import create_access_token
from app.models.token import Token
from app.models.user import User
from app.schemas.token_schema import TokenCreate, TokenResponse
from app.services.device_service import DeviceService
from app.utils.db import db
from app.utils.generator import calculate_minutes_between_dates
from app.utils.logger import get_logger

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
datetime_jpn = datetime.now(tz=pytz.UTC)


class TokenService:
    @staticmethod
    async def create_token(token: TokenCreate, user: User):
        try:
            logger.info(token)
            now = datetime.now(tz=pytz.UTC)
            minutes = calculate_minutes_between_dates(now, token.expires_at)
            logger.warn(f"token will be expired in {minutes} minutes")
            expire = timedelta(minutes=minutes)
            device = await DeviceService.get_device(token.device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
            payload = {
                "user_id": str(user.id),
                "username": user.username,
                "device_id": str(device.id),
                "device_code": device.code
            }
            access_token = create_access_token(payload, expires_delta=expire)
            new_token: Token = Token(
                device_id=token.device_id,
                name=token.name,
                token=access_token,
                description=token.description,
                expires_at=token.expires_at,
                inserted_at=datetime_jpn,
                inserted_by=str(user.id)
            )
            logger.info(new_token)
            new_token_inserted = await db.tokens.insert_one(new_token.model_dump(by_alias=True))
            new_token_id = new_token_inserted.inserted_id
            return TokenResponse(_id=new_token_id,
                                 device_id=token.device_id,
                                 name=token.name,
                                 token=access_token,
                                 description=token.description,
                                 expires_at=token.expires_at,
                                 inserted_at=datetime_jpn,
                                 inserted_by=str(user.id)
                                 )
        except Exception as e:
            logger.error(f"Failed to create token: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_token(token_id: str):
        try:
            token = await db.tokens.find_one({"_id": ObjectId(token_id)})
            if token:
                return TokenResponse(**token)
            raise HTTPException(status_code=404, detail="Token not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_token_by_device(device_id: str):
        try:

            token = await db.tokens.find({
                "device_id": device_id,
                "deleted_at": {"$eq": None},
                "expires_at": {"$gte": datetime.now()}
            })
            if token:
                return TokenResponse(**token)
            raise HTTPException(status_code=404, detail="Token not found")

        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_all_tokens():
        try:
            tokens = []
            cursor = db.tokens.find({})
            async for token in cursor:
                logger.info(f"{token} {token["_id"]}")
                token_response = TokenResponse(**token)
                tokens.append(token_response)
                logger.info("")
            return tokens
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_token(token_id: str, current_user: str):
        try:
            update_data = {
                "deleted_at": datetime_jpn,
                "deleted_by": current_user
            }
            result = await db.tokens.update_one({"_id": ObjectId(token_id)}, {"$set": update_data})
            if result.matched_count == 1:
                return True
            return False
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
