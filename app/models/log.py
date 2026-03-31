from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class LogCategory(str, Enum):
    CRUD = "CRUD"
    AUTH = "AUTH"
    ERROR = "ERROR"
    SYSTEM = "SYSTEM"
    QUERY = "QUERY"
    API = "API"


class LogEntry(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    module: str
    action: str
    entity: Optional[str] = None
    category: LogCategory = LogCategory.SYSTEM
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    system_context: Dict[str, Any] = Field(default_factory=dict)
    embedding_text: Optional[str] = None

    def to_embedding_string(self) -> str:
        parts = [
            f"user:{self.user_id}",
            f"module:{self.module}",
            f"action:{self.action}",
        ]
        if self.entity:
            parts.append(f"entity:{self.entity}")
        parts.append(f"category:{self.category.value}")
        if self.description:
            parts.append(f"desc:{self.description}")
        if self.metadata:
            for k, v in self.metadata.items():
                parts.append(f"{k}:{v}")
        return " | ".join(parts)


class LogCreateRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user (token, PK, UUID — any consistent format)")
    module: str = Field(..., description="Module or service name (e.g. 'inventory', 'auth', 'orders')")
    action: str = Field(..., description="Action performed (e.g. 'create_item', 'login', 'update_stock')")
    entity: Optional[str] = Field(None, description="Entity affected (e.g. 'product', 'order', 'session')")
    category: LogCategory = Field(LogCategory.SYSTEM, description="Log classification")
    description: Optional[str] = Field(None, description="Human-readable description of the event")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary key-value context")


class LogBatchRequest(BaseModel):
    logs: List[LogCreateRequest] = Field(..., min_length=1, max_length=100)


class LogQueryParams(BaseModel):
    user_id: str
    module: Optional[str] = None
    category: Optional[LogCategory] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=500)
    skip: int = Field(0, ge=0)
