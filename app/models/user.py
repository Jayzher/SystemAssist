from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    user_id: Optional[str] = Field(
        None,
        description="User identifier. Required when authenticating via X-Api-Key. "
                    "Omit when authenticating via X-Session-Token (user_id is read from the session).",
    )
    query: str = Field(..., description="User's question about their activity")
    session_id: Optional[str] = Field(
        None,
        description="Chat session ID for follow-up conversations. Omit to start a new chat session.",
    )
    limit: int = Field(10, ge=1, le=50, description="Max log entries to search")


class SummaryRequest(BaseModel):
    user_id: str = Field(..., description="Same identifier used in log entries")
    days: int = Field(7, ge=1, le=90, description="Number of days to look back")
    module: Optional[str] = Field(None, description="Filter to a specific module")
