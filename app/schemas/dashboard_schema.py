from typing import Optional
from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    edge_online_count: int
    edge_offline_count: int
    end_device_count: int
    active_key_generation: int
    latest_firmware_version: Optional[str] = None
