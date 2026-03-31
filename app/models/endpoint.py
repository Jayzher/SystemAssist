import uuid
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    user_id: str = Field(..., description="Dot-notation path to user identifier in source JSON (e.g. 'user.id')")
    module: Optional[str] = Field(None, description="Path to module/service name (e.g. 'service')")
    action: Optional[str] = Field(None, description="Path to action/event name (e.g. 'event.type')")
    entity: Optional[str] = Field(None, description="Path to entity/resource name (e.g. 'resource')")
    category: Optional[str] = Field(None, description="Path to log level/category (e.g. 'severity')")
    description: Optional[str] = Field(None, description="Path to human-readable message (e.g. 'message')")
    metadata: Optional[str] = Field(None, description="Path to extra payload/data object (e.g. 'data')")


class RegisteredEndpoint(BaseModel):
    endpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    field_mapping: FieldMapping
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ingest_count: int = 0


class EndpointCreate(BaseModel):
    name: str = Field(..., description="Friendly name for the connected app")
    description: Optional[str] = Field(None, description="What system this endpoint receives logs from")
    field_mapping: FieldMapping


class IngestPreviewRequest(BaseModel):
    field_mapping: FieldMapping
    sample_data: Dict[str, Any]
