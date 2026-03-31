import asyncio
import gzip
import json
import re
import base64
from datetime import datetime
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.security.rbac import verify_api_key
from app.services.log_service import create_log, create_logs_batch, get_logs_for_embedding
from app.services.embedding_service import build_index
from app.models.log import LogCreateRequest, LogBatchRequest, LogCategory

router = APIRouter(tags=["session"])

# ── Log line parser ──────────────────────────────────────────────────────────

_LINE_RE = re.compile(
    r'^\[(?P<level>\w+)\]\s+(?P<ts>[\d\-]+ [\d:,]+)\s+(?P<module>[\w.]+)'
    r'\s+[\u2014\-]+\s+(?P<msg>.+)$'
)
_USER_RE   = re.compile(r'user=(\S+)')
_ACTION_RE = re.compile(r'action=(\S+)')
_ENTITY_RE = re.compile(r'entity=(\S+)')


def _parse_log_line(line: str, default_user_id: str) -> Optional[LogCreateRequest]:
    line = line.strip()
    if not line:
        return None
    m = _LINE_RE.match(line)
    if not m:
        return None

    level   = m.group('level')
    ts_str  = m.group('ts').split(',')[0]
    module  = m.group('module')
    msg     = m.group('msg')

    user_m   = _USER_RE.search(msg)
    action_m = _ACTION_RE.search(msg)
    entity_m = _ENTITY_RE.search(msg)

    user_id = user_m.group(1)   if user_m   else default_user_id
    action  = action_m.group(1) if action_m else 'log'
    entity  = entity_m.group(1) if entity_m else None

    desc_parts  = msg.split('\u2014')
    description = desc_parts[-1].strip() if len(desc_parts) > 1 else msg

    if level == 'ERROR':
        category = LogCategory.ERROR
    elif action in ('login', 'logout', 'register'):
        category = LogCategory.AUTH
    elif 'system' in module:
        category = LogCategory.SYSTEM
    else:
        category = LogCategory.CRUD

    return LogCreateRequest(
        user_id=user_id,
        module=module,
        action=action,
        entity=entity,
        category=category,
        description=description,
        metadata={'source': 'context_upload', 'level': level, 'ts': ts_str},
    )


# ── POST /api/context ────────────────────────────────────────────────────────

class ContextUploadRequest(BaseModel):
    user_id: str
    source: str           # "system" | "user_actions"
    content_gz_b64: str   # gzipped, base64-encoded log text


@router.post("/api/context", summary="Upload compressed historical logs as AI context")
async def upload_context(req: ContextUploadRequest, _: str = Depends(verify_api_key)):
    try:
        raw   = base64.b64decode(req.content_gz_b64)
        text  = gzip.decompress(raw).decode('utf-8', errors='replace')
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Decompression failed: {exc}")

    entries = [
        e for e in (_parse_log_line(l, req.user_id) for l in text.splitlines()) if e
    ]

    if not entries:
        return {"status": "ok", "parsed": 0}

    total = 0
    for i in range(0, len(entries), 100):
        chunk = LogBatchRequest(logs=entries[i:i + 100])
        await create_logs_batch(chunk.logs, {"ip": "internal", "user_agent": "context-upload"})
        total += len(chunk.logs)

    asyncio.create_task(_reindex())
    return {"status": "ok", "source": req.source, "parsed": total}


async def _reindex() -> None:
    try:
        docs = await get_logs_for_embedding(user_id=None)
        build_index(docs)
    except Exception:
        pass


# ── WebSocket /ws/session/{user_id} ─────────────────────────────────────────

@router.websocket("/ws/session/{user_id}")
async def session_ws(websocket: WebSocket, user_id: str):
    from app.config import settings as sa_settings

    api_key = (
        websocket.query_params.get("api_key")
        or websocket.headers.get("x-api-key", "")
    )
    if api_key != sa_settings.api_key:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")

            if mtype == "log":
                p = msg.get("payload", {})
                try:
                    req = LogCreateRequest(
                        user_id=p.get("user_id", user_id),
                        module=p.get("module", "unknown"),
                        action=p.get("action", "log"),
                        entity=p.get("entity"),
                        category=p.get("category", "SYSTEM"),
                        description=p.get("description"),
                        metadata={**p.get("metadata", {}), "source": "ws_session"},
                    )
                    await create_log(req, {"ip": "ws", "user_agent": "session-stream"})
                    await websocket.send_text(json.dumps({"status": "ok"}))
                except Exception as exc:
                    await websocket.send_text(json.dumps({"status": "error", "detail": str(exc)}))
                else:
                    asyncio.create_task(_reindex())

            elif mtype == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
