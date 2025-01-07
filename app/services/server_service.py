#   """
#   Copyright (c) 2025 lepen - All Rights Reserved
#   Created by lepen on 2025-01-07 12:09:20
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2025-01-07 12:09:20
#   File: ServerService.py
#   Description:
#   """
import traceback

from fastapi import HTTPException

from app.schemas.server_schema import ServerResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ServerService:
    @staticmethod
    async def get_server_config(protocol: str, environment: str = "development"):
        try:
            server = await db.servers.find_one(
                {"protocol": {"$eq": protocol}, "environment": {"$eq": environment}})
            if server:
                return ServerResponse(**server)
            raise HTTPException(status_code=404, detail="Server configuration not found")
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
