from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
from app.services.database import get_db
from app.security.rbac import verify_api_key, get_user_context

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", summary="Get overall log statistics and analytics")
async def get_stats(
    user_id: Optional[str] = Query(None, description="Filter stats to a specific user"),
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    _: str = Depends(verify_api_key),
):
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=days)
    match_stage = {"timestamp": {"$gte": cutoff}}
    if user_id:
        match_stage["user_id"] = user_id

    # Total count
    total = await db.logs.count_documents(match_stage)

    # Count by category
    cat_pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cat_cursor = db.logs.aggregate(cat_pipeline)
    categories = {doc["_id"]: doc["count"] async for doc in cat_cursor}

    # Count by module
    mod_pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$module", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    mod_cursor = db.logs.aggregate(mod_pipeline)
    modules = {doc["_id"]: doc["count"] async for doc in mod_cursor}

    # Activity timeline (per day)
    timeline_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    timeline_cursor = db.logs.aggregate(timeline_pipeline)
    timeline = [{"date": doc["_id"], "count": doc["count"]} async for doc in timeline_cursor]

    # Recent active users (top 10)
    users_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$user_id",
            "count": {"$sum": 1},
            "last_active": {"$max": "$timestamp"},
        }},
        {"$sort": {"last_active": -1}},
        {"$limit": 10},
    ]
    users_cursor = db.logs.aggregate(users_pipeline)
    active_users = [
        {"user_id": doc["_id"], "count": doc["count"],
         "last_active": doc["last_active"].isoformat() if hasattr(doc["last_active"], "isoformat") else str(doc["last_active"])}
        async for doc in users_cursor
    ]

    # Error rate
    error_count = categories.get("ERROR", 0)
    error_rate = round((error_count / total * 100), 1) if total > 0 else 0

    # Top actions
    action_pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    action_cursor = db.logs.aggregate(action_pipeline)
    top_actions = [{"action": doc["_id"], "count": doc["count"]} async for doc in action_cursor]

    return {
        "status": "ok",
        "period_days": days,
        "total_logs": total,
        "error_rate": error_rate,
        "categories": categories,
        "modules": modules,
        "timeline": timeline,
        "active_users": active_users,
        "top_actions": top_actions,
    }


@router.get("/user/{user_id}", summary="Get detailed stats for a specific user")
async def get_user_stats(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    user_ctx: dict = Depends(get_user_context),
):
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=days)
    match_stage = {"user_id": user_id, "timestamp": {"$gte": cutoff}}

    total = await db.logs.count_documents(match_stage)

    cat_pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    categories = {doc["_id"]: doc["count"] async for doc in db.logs.aggregate(cat_pipeline)}

    mod_pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$module", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    modules = {doc["_id"]: doc["count"] async for doc in db.logs.aggregate(mod_pipeline)}

    # Hourly distribution
    hourly_pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": {"$hour": "$timestamp"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    hourly = {doc["_id"]: doc["count"] async for doc in db.logs.aggregate(hourly_pipeline)}

    # Recent errors
    error_cursor = db.logs.find(
        {**match_stage, "category": "ERROR"},
        {"_id": 0, "log_id": 1, "timestamp": 1, "module": 1, "action": 1, "description": 1},
    ).sort("timestamp", -1).limit(5)
    recent_errors = await error_cursor.to_list(length=5)
    for e in recent_errors:
        if hasattr(e.get("timestamp"), "isoformat"):
            e["timestamp"] = e["timestamp"].isoformat()

    error_count = categories.get("ERROR", 0)
    error_rate = round((error_count / total * 100), 1) if total > 0 else 0

    return {
        "status": "ok",
        "user_id": user_id,
        "period_days": days,
        "total_logs": total,
        "error_rate": error_rate,
        "categories": categories,
        "modules": modules,
        "hourly_distribution": hourly,
        "recent_errors": recent_errors,
    }
