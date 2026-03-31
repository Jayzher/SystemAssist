from fastapi import APIRouter, Depends, Request
from typing import Optional
from datetime import datetime
from app.models.log import LogCreateRequest, LogBatchRequest, LogQueryParams, LogCategory
from app.services.log_service import create_log, create_logs_batch, get_logs
from app.security.rbac import verify_api_key

router = APIRouter(prefix="/api/logs", tags=["logs"], dependencies=[Depends(verify_api_key)])


@router.post("", summary="Create a single log entry")
async def create_log_entry(log_data: LogCreateRequest, request: Request):
    system_context = {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
    }
    entry = await create_log(log_data, system_context)
    return {"status": "ok", "log_id": entry.log_id}


@router.post("/batch", summary="Create multiple log entries at once (max 100)")
async def create_log_batch(batch: LogBatchRequest, request: Request):
    system_context = {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
    }
    log_ids = await create_logs_batch(batch.logs, system_context)
    return {"status": "ok", "count": len(log_ids), "log_ids": log_ids}


@router.get("", summary="Fetch logs for a specific user_id")
async def fetch_logs(
    user_id: str,
    module: Optional[str] = None,
    category: Optional[LogCategory] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    skip: int = 0,
):
    params = LogQueryParams(
        user_id=user_id,
        module=module,
        category=category,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        skip=skip,
    )
    results = await get_logs(params)
    return {"status": "ok", "count": len(results), "logs": results}
