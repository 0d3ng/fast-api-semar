from datetime import datetime
from typing import Optional, Any, List, Dict

from pydantic import BaseModel, Field, ConfigDict

from app.utils.custom_fields import PydanticObjectId


class ConfigUpdateRequest(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias='_id', default_factory=PydanticObjectId)
    target_scope: str = "selected"  # all | selected
    edge_id: Optional[str] = None
    target_device_ids: List[str] = []
    config_payload: Dict[str, Any] = {}
    status: str = "pending"  # pending | in_progress | completed | completed_partial | failed
    device_results: List[Dict[str, Any]] = []
    requested_by: Optional[str] = None
    requested_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    inserted_at: Optional[datetime] = None
    inserted_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
