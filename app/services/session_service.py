from datetime import datetime, timedelta
from typing import Optional, List
from app.models.user import ChatSession, ChatMessage
from app.services.database import get_db
from app.config import settings


async def get_or_create_session(user_id: str, session_id: Optional[str] = None) -> ChatSession:
    db = get_db()

    if session_id:
        doc = await db.chat_sessions.find_one({"session_id": session_id, "user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return ChatSession(**doc)

    session = ChatSession(user_id=user_id)
    await db.chat_sessions.insert_one(session.model_dump())
    return session


async def append_message(session_id: str, role: str, content: str) -> None:
    db = get_db()
    msg = ChatMessage(role=role, content=content)
    await db.chat_sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": msg.model_dump()},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )


async def get_conversation_history(session_id: str, max_turns: int = 6) -> List[ChatMessage]:
    db = get_db()
    doc = await db.chat_sessions.find_one({"session_id": session_id})
    if not doc or not doc.get("messages"):
        return []
    messages = [ChatMessage(**m) for m in doc["messages"]]
    return messages[-max_turns:]


async def cleanup_expired_chat_sessions() -> int:
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(hours=settings.session_ttl_hours)
    result = await db.chat_sessions.delete_many({"updated_at": {"$lt": cutoff}})
    return result.deleted_count
