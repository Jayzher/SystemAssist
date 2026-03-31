import uuid
import secrets
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class RegisteredApp(BaseModel):
    app_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    api_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    allowed_domain: str
    owner_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class AppCreateRequest(BaseModel):
    name: str = Field(..., description="Human-friendly name for the application")
    description: Optional[str] = Field(None, description="What this app does")
    allowed_domain: str = Field(
        ...,
        description="Allowed origin domain (e.g. 'myapp.com', 'localhost:3000'). "
                    "Browser requests from other origins are rejected.",
    )
    owner_name: Optional[str] = Field(None, description="Owner / team name")


class UserSession(BaseModel):
    session_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    user_id: str
    app_id: str
    app_name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    last_active_at: datetime = Field(default_factory=datetime.utcnow)


class CreateUserSessionRequest(BaseModel):
    user_id: str = Field(..., description="User identifier from the calling application")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional user metadata (display name, role, etc.)",
    )
