import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.log import LogEntry, LogCreateRequest, LogQueryParams, LogCategory
from app.services.database import get_db
from app.services.embedding_service import add_to_index

logger = logging.getLogger(__name__)


async def create_log(log_data: LogCreateRequest, system_context: Optional[Dict[str, Any]] = None) -> LogEntry:
    entry = LogEntry(
        user_id=log_data.user_id,
        module=log_data.module,
        action=log_data.action,
        entity=log_data.entity,
        category=log_data.category,
        description=log_data.description,
        metadata=log_data.metadata,
        system_context=system_context or {},
    )
    entry.embedding_text = entry.to_embedding_string()
    db = get_db()
    doc = entry.model_dump()
    await db.logs.insert_one(doc)
    try:
        await asyncio.to_thread(add_to_index, doc)
    except Exception as exc:
        logger.warning("add_to_index failed for log %s — %s", entry.log_id, exc)
    return entry


async def create_logs_batch(logs: List[LogCreateRequest], system_context: Optional[Dict[str, Any]] = None) -> List[str]:
    entries = []
    for log_data in logs:
        entry = LogEntry(
            user_id=log_data.user_id,
            module=log_data.module,
            action=log_data.action,
            entity=log_data.entity,
            category=log_data.category,
            description=log_data.description,
            metadata=log_data.metadata,
            system_context=system_context or {},
        )
        entry.embedding_text = entry.to_embedding_string()
        entries.append(entry)

    db = get_db()
    docs = [e.model_dump() for e in entries]
    await db.logs.insert_many(docs)
    for doc in docs:
        try:
            await asyncio.to_thread(add_to_index, doc)
        except Exception as exc:
            logger.warning("add_to_index failed for log %s — %s", doc.get("log_id"), exc)
    return [e.log_id for e in entries]


async def get_logs(params: LogQueryParams) -> List[dict]:
    db = get_db()
    query: Dict[str, Any] = {"user_id": params.user_id}

    if params.module:
        query["module"] = params.module
    if params.category:
        query["category"] = params.category.value

    date_filter = {}
    if params.start_date:
        date_filter["$gte"] = params.start_date
    if params.end_date:
        date_filter["$lte"] = params.end_date
    if date_filter:
        query["timestamp"] = date_filter

    cursor = (
        db.logs.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(params.skip)
        .limit(params.limit)
    )
    return await cursor.to_list(length=params.limit)


async def get_user_log_ids(user_id: str) -> List[str]:
    db = get_db()
    cursor = db.logs.find({"user_id": user_id}, {"log_id": 1, "_id": 0})
    docs = await cursor.to_list(length=10000)
    return [d["log_id"] for d in docs]


async def get_logs_for_embedding(user_id: Optional[str] = None) -> List[dict]:
    db = get_db()
    query = {}
    if user_id:
        query["user_id"] = user_id
    cursor = db.logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(5000)
    return await cursor.to_list(length=5000)


async def get_logs_by_ids(log_ids: List[str]) -> List[dict]:
    db = get_db()
    cursor = db.logs.find({"log_id": {"$in": log_ids}}, {"_id": 0})
    return await cursor.to_list(length=len(log_ids))
