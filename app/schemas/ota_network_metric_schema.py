from datetime import datetime
from typing import Optional, Any, Union, List, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.utils.custom_fields import PydanticObjectId
from app.models.ota_network_metric import DeviceNetworkMetric, NetworkMetricSummary


class OtaNetworkMetricCreate(BaseModel):
    session_id: Optional[Union[int, str, Any]] = None
    edge_id: Optional[str] = None
    devices_count: Optional[int] = None
    device_count: Optional[int] = None
    protocol: str  # multicast | unicast | http
    firmware_size_bytes: Optional[int] = 0
    summary: NetworkMetricSummary
    tx_breakdown: Optional[Dict[str, Any]] = None
    rx_breakdown: Optional[Dict[str, Any]] = None
    devices_metrics: Optional[List[DeviceNetworkMetric]] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OtaNetworkMetricResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    session_id: Union[int, str, Any]
    edge_id: str
    devices_count: Optional[int] = 1
    protocol: str
    firmware_size_bytes: Optional[int] = 0
    summary: NetworkMetricSummary
    tx_breakdown: Optional[Dict[str, Any]] = None
    rx_breakdown: Optional[Dict[str, Any]] = None
    devices_metrics: Optional[List[DeviceNetworkMetric]] = []
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def populate_devices_count(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "devices_count" not in data or data["devices_count"] is None:
                devs = data.get("devices_metrics") or []
                data["devices_count"] = len(devs) or 1
        return data

    @field_validator('inserted_at', 'updated_at', 'deleted_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProtocolComparisonItem(BaseModel):
    session_id: Union[int, str, Any]
    protocol: str
    edge_id: str
    firmware_size_bytes: int
    devices_count: int
    duration_seconds: Optional[float] = None
    total_tx_bytes: int
    total_rx_bytes: int
    total_load_bytes: int
    retransmission_bytes: int = 0
    retransmission_ratio_pct: float = 0.0
    wire_amplification_factor: float = 0.0
    throughput_kbps: float = 0.0


class NetworkComparisonResponse(BaseModel):
    sessions: List[ProtocolComparisonItem] = []
    summary: Dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)
