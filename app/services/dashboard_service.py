import traceback
from fastapi import HTTPException

from app.schemas.dashboard_schema import DashboardSummaryResponse
from app.utils.db import db
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashboardService:
    @staticmethod
    async def get_summary():
        try:
            edge_online_count = await db.ota_edges.count_documents({"status": "online", "deleted_at": None})
            edge_offline_count = await db.ota_edges.count_documents({"status": {"$ne": "online"}, "deleted_at": None})
            end_device_count = await db.ota_end_devices.count_documents({"deleted_at": None})

            latest_release = await db.ota_firmware_releases.find_one(
                {"deleted_at": None},
                sort=[("key_generation", -1), ("inserted_at", -1)]
            )

            active_key_gen = latest_release.get("key_generation", 1) if latest_release else 1
            latest_fw_version = latest_release.get("target_version") if latest_release else None

            return DashboardSummaryResponse(
                edge_online_count=edge_online_count,
                edge_offline_count=edge_offline_count,
                end_device_count=end_device_count,
                active_key_generation=active_key_gen,
                latest_firmware_version=latest_fw_version
            )
        except Exception as e:
            logger.error(f"Failed to fetch dashboard summary: {e}")
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            logger.error(f"{e}\n{tb_str}")
            raise HTTPException(status_code=500, detail=str(e))
