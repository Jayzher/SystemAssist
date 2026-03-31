from typing import List, Optional
from app.models.session import RegisteredApp, AppCreateRequest
from app.services.database import get_db


async def create_app(data: AppCreateRequest) -> RegisteredApp:
    db = get_db()
    app = RegisteredApp(**data.model_dump())
    await db.registered_apps.insert_one(app.model_dump())
    return app


async def get_app_by_api_key(api_key: str) -> Optional[dict]:
    db = get_db()
    return await db.registered_apps.find_one(
        {"api_key": api_key, "is_active": True}, {"_id": 0}
    )


async def get_apps() -> List[dict]:
    db = get_db()
    cursor = db.registered_apps.find({}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=500)


async def get_app(app_id: str) -> Optional[dict]:
    db = get_db()
    return await db.registered_apps.find_one({"app_id": app_id}, {"_id": 0})


async def delete_app(app_id: str) -> bool:
    db = get_db()
    result = await db.registered_apps.delete_one({"app_id": app_id})
    return result.deleted_count > 0


async def set_app_active(app_id: str, is_active: bool) -> bool:
    db = get_db()
    result = await db.registered_apps.update_one(
        {"app_id": app_id},
        {"$set": {"is_active": is_active}},
    )
    return result.modified_count > 0
