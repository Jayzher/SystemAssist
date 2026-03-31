from datetime import datetime, timedelta
from typing import Optional
from app.models.session import UserSession
from app.services.database import get_db
from app.config import settings


async def create_user_session(
    user_id: str,
    app_id: str,
    app_name: str,
    metadata: Optional[dict] = None,
) -> UserSession:
    db = get_db()
    now = datetime.utcnow()
    ttl = timedelta(minutes=settings.user_session_ttl_minutes)
    session = UserSession(
        user_id=user_id,
        app_id=app_id,
        app_name=app_name,
        metadata=metadata or {},
        created_at=now,
        expires_at=now + ttl,
        last_active_at=now,
    )
    await db.users_session.insert_one(session.model_dump())
    return session


async def get_user_session(session_token: str) -> Optional[dict]:
    db = get_db()
    return await db.users_session.find_one(
        {
            "session_token": session_token,
            "expires_at": {"$gt": datetime.utcnow()},
        },
        {"_id": 0},
    )


async def extend_user_session(session_token: str) -> bool:
    db = get_db()
    new_expiry = datetime.utcnow() + timedelta(minutes=settings.user_session_ttl_minutes)
    result = await db.users_session.update_one(
        {
            "session_token": session_token,
            "expires_at": {"$gt": datetime.utcnow()},
        },
        {
            "$set": {
                "expires_at": new_expiry,
                "last_active_at": datetime.utcnow(),
            }
        },
    )
    return result.modified_count > 0


async def invalidate_user_session(session_token: str) -> bool:
    db = get_db()
    result = await db.users_session.delete_one({"session_token": session_token})
    return result.deleted_count > 0


async def cleanup_expired_user_sessions() -> int:
    db = get_db()
    result = await db.users_session.delete_many(
        {"expires_at": {"$lt": datetime.utcnow()}}
    )
    return result.deleted_count
