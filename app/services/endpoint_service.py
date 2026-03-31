from typing import List, Optional
from app.models.endpoint import RegisteredEndpoint, EndpointCreate
from app.services.database import get_db


async def create_endpoint(data: EndpointCreate) -> RegisteredEndpoint:
    db = get_db()
    endpoint = RegisteredEndpoint(**data.model_dump())
    await db.registered_endpoints.insert_one(endpoint.model_dump())
    return endpoint


async def get_endpoints() -> List[dict]:
    db = get_db()
    cursor = db.registered_endpoints.find({}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=500)


async def get_endpoint(endpoint_id: str) -> Optional[dict]:
    db = get_db()
    return await db.registered_endpoints.find_one({"endpoint_id": endpoint_id}, {"_id": 0})


async def delete_endpoint(endpoint_id: str) -> bool:
    db = get_db()
    result = await db.registered_endpoints.delete_one({"endpoint_id": endpoint_id})
    return result.deleted_count > 0


async def increment_ingest_count(endpoint_id: str):
    db = get_db()
    await db.registered_endpoints.update_one(
        {"endpoint_id": endpoint_id},
        {"$inc": {"ingest_count": 1}},
    )
