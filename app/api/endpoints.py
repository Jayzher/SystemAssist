from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from app.models.endpoint import EndpointCreate, FieldMapping, IngestPreviewRequest
from app.services.endpoint_service import (
    create_endpoint, get_endpoints, get_endpoint,
    delete_endpoint, increment_ingest_count,
)
from app.services.log_service import create_log
from app.models.log import LogCreateRequest
from app.services.normalizer import normalize
from app.security.rbac import verify_api_key

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


@router.post("")
async def register_endpoint(data: EndpointCreate, _: str = Depends(verify_api_key)):
    endpoint = await create_endpoint(data)
    return {"status": "ok", "endpoint_id": endpoint.endpoint_id, "name": endpoint.name}


@router.get("")
async def list_endpoints(_: str = Depends(verify_api_key)):
    eps = await get_endpoints()
    return {"status": "ok", "count": len(eps), "endpoints": eps}


@router.delete("/{endpoint_id}")
async def remove_endpoint(endpoint_id: str, _: str = Depends(verify_api_key)):
    deleted = await delete_endpoint(endpoint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return {"status": "ok"}


@router.post("/preview")
async def preview_normalization(body: IngestPreviewRequest, _: str = Depends(verify_api_key)):
    result = normalize(body.sample_data, body.field_mapping)
    return {"status": "ok", "normalized": result}


@router.post("/{endpoint_id}/ingest")
async def ingest(endpoint_id: str, payload: Dict[str, Any], _: str = Depends(verify_api_key)):
    ep = await get_endpoint(endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    mapping = FieldMapping(**ep["field_mapping"])
    normalized = normalize(payload, mapping, app_name=ep["name"])

    if normalized["user_id"] == "unknown":
        raise HTTPException(
            status_code=422,
            detail="Could not extract user_id from payload. Check your field_mapping.user_id path.",
        )

    log_req = LogCreateRequest(
        user_id=normalized["user_id"],
        module=normalized["module"],
        action=normalized["action"],
        entity=normalized.get("entity"),
        category=normalized["category"],
        description=normalized.get("description"),
        metadata=normalized.get("metadata", {}),
    )
    entry = await create_log(log_req, system_context=normalized.get("system_context", {}))
    await increment_ingest_count(endpoint_id)
    return {"status": "ok", "log_id": entry.log_id}


@router.post("/{endpoint_id}/ingest/batch")
async def ingest_batch(endpoint_id: str, payloads: List[Dict[str, Any]], _: str = Depends(verify_api_key)):
    ep = await get_endpoint(endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    mapping = FieldMapping(**ep["field_mapping"])
    results = []
    errors = []

    for i, payload in enumerate(payloads):
        normalized = normalize(payload, mapping, app_name=ep["name"])
        if normalized["user_id"] == "unknown":
            errors.append({"index": i, "error": "Could not extract user_id"})
            continue
        log_req = LogCreateRequest(
            user_id=normalized["user_id"],
            module=normalized["module"],
            action=normalized["action"],
            entity=normalized.get("entity"),
            category=normalized["category"],
            description=normalized.get("description"),
            metadata=normalized.get("metadata", {}),
        )
        entry = await create_log(log_req, system_context=normalized.get("system_context", {}))
        results.append(entry.log_id)

    if results:
        await increment_ingest_count(endpoint_id)

    return {"status": "ok", "count": len(results), "log_ids": results, "errors": errors}
