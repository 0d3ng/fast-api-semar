from datetime import datetime
from typing import Optional, Any, List, Dict

from pydantic import Field, ConfigDict, BaseModel, field_validator

from app.utils.custom_fields import PydanticObjectId


class ConfigPayloadSchema(BaseModel):
    wifi_ssid: Optional[str] = None
    wifi_password: Optional[str] = None
    ntp_server: Optional[str] = None
    device_id: Optional[str] = None
    ota_protocol: Optional[str] = None
    multicast_ip: Optional[str] = None
    multicast_port: Optional[int] = None
    unicast_ip: Optional[str] = None
    unicast_port: Optional[int] = None
    edge_url: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


class ConfigUpdateRequestCreate(BaseModel):
    target_scope: str = "selected"  # all | selected
    edge_id: Optional[str] = None
    target_device_ids: List[str] = []
    config: ConfigPayloadSchema

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ConfigUpdateAckPayload(BaseModel):
    device_id: str
    status: str = "success"  # success | failed
    reason: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ConfigUpdateRequestResponse(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    target_scope: str
    edge_id: Optional[str] = None
    target_device_ids: List[str] = []
    config_payload: Dict[str, Any] = {}
    status: str
    device_results: List[Dict[str, Any]] = []
    requested_by: Optional[str] = None
    requested_at: Optional[str] = None
    completed_at: Optional[str] = None
    inserted_at: Optional[str] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

    @field_validator('requested_at', 'completed_at', 'inserted_at', 'updated_at', mode='before')
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                import pytz
                v = pytz.UTC.localize(v)
            return v.strftime('%Y-%m-%d %H:%M:%S')
        return v

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    )
