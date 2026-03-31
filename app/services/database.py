import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.config import settings

_client: AsyncIOMotorClient = None
_db = None


async def connect_db():
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    _db = _client[settings.mongodb_db_name]

    await _db.logs.create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("category", ASCENDING)]),
        IndexModel([("module", ASCENDING)]),
        IndexModel([("log_id", ASCENDING)], unique=True),
    ])
    await _db.chat_sessions.create_indexes([
        IndexModel([("session_id", ASCENDING)], unique=True),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("updated_at", DESCENDING)]),
    ])
    await _db.registered_endpoints.create_indexes([
        IndexModel([("endpoint_id", ASCENDING)], unique=True),
        IndexModel([("name", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])
    await _db.registered_apps.create_indexes([
        IndexModel([("app_id", ASCENDING)], unique=True),
        IndexModel([("api_key", ASCENDING)], unique=True),
        IndexModel([("allowed_domain", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])
    await _db.users_session.create_indexes([
        IndexModel([("session_token", ASCENDING)], unique=True),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("app_id", ASCENDING)]),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
    ])
    return _db


async def close_db():
    global _client
    if _client:
        _client.close()


def get_db():
    return _db
