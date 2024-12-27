#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:45:51
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-12-04 21:05:08
#  File: auth.py
#  Description:
#  """

import traceback
from datetime import datetime, timedelta

import pytz
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.schemas.token_schema import TokenData, TokenDataDevice
from app.utils.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET
from app.utils.logger import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(pytz.UTC) + expires_delta
    else:
        expire = datetime.now(pytz.UTC) + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    logger.info(to_encode)
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        if username is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, username=username)
    except (JWTError, Exception) as e:
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        logger.error(f"{e}\n{tb_str}")
        raise credentials_exception
    return token_data


def verify_token_device(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        device_id: str = payload.get("device_id")
        device_code: str = payload.get("device_code")
        if device_id is None:
            raise Exception("device_id is None")
        token_data = TokenDataDevice(user_id=user_id, username=username, device_id=device_id, device_code=device_code)
    except (JWTError, Exception) as e:
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        logger.error(f"{e}\n{tb_str}")
        raise Exception
    return token_data
