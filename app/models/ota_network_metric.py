from datetime import datetime
from typing import Optional, Any, Union, List, Dict
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.utils.custom_fields import PydanticObjectId


class DeviceNetworkMetric(BaseModel):
    device_id: str = ""
    ack_status: Optional[str] = "unknown"
    total_duration_ms: Optional[int] = None
    duration_seconds: Optional[float] = None
    tx_bytes: int = 0
    rx_bytes: int = 0
    total_bytes: int = 0
    chunks_sent: int = 0
    chunks_retransmitted: int = 0
    nack_count: int = 0

    @model_validator(mode='before')
    @classmethod
    def sync_device_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            dev_id = data.get("device_id") or data.get("end_device_id") or ""
            data["device_id"] = str(dev_id)
        return data

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)


class NetworkMetricSummary(BaseModel):
    total_tx_bytes: int = 0
    total_rx_bytes: int = 0
    total_load_bytes: int = 0
    duration_seconds: Optional[float] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OtaNetworkMetric(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    session_id: Union[int, str, Any]
    edge_id: str
    devices_count: Optional[int] = 1
    protocol: str  # multicast | unicast | http
    firmware_size_bytes: Optional[int] = 0
    summary: NetworkMetricSummary
    tx_breakdown: Optional[Dict[str, Any]] = None
    rx_breakdown: Optional[Dict[str, Any]] = None
    devices_metrics: Optional[List[DeviceNetworkMetric]] = []
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
