#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-01 19:04:49
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-01 19:04:49
#  File: widget_service.py
#  Description:
#  """
import traceback
from datetime import datetime

import pytz
from fastapi import HTTPException

from app.schemas.widget_schema import WidgetResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)
datetime_jpn = datetime.now(tz=pytz.UTC)


class WidgetService:
    @staticmethod
    async def get_all_widgets(user_id: str = None):
        try:
            widgets = []
            if user_id:
                filter = {"inserted_by": user_id}
            else:
                filter = {}
            cursor = db.widgets.find(filter)
            async for widget in cursor:
                logger.info(f"{widget} {widget["_id"]}")
                widget_response = WidgetResponse(**widget)
                widgets.append(widget_response)
                logger.info("")
            return widgets
        except (KeyError, TypeError, Exception) as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
