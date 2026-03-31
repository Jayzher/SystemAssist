from fastapi import APIRouter, Depends, HTTPException
from app.models.session import AppCreateRequest
from app.services.app_service import create_app, get_apps, get_app, delete_app, set_app_active
from app.security.rbac import verify_api_key

router = APIRouter(
    prefix="/api/apps",
    tags=["apps"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", summary="Register a new application and receive its API key")
async def register_app(data: AppCreateRequest):
    app = await create_app(data)
    return {
        "status": "ok",
        "app_id": app.app_id,
        "name": app.name,
        "api_key": app.api_key,
        "allowed_domain": app.allowed_domain,
        "message": (
            "Store this API key securely — it is shown only once in full here. "
            "Use X-App-Api-Key header to authenticate session creation requests."
        ),
    }


@router.get("", summary="List all registered applications")
async def list_apps():
    apps = await get_apps()
    return {"status": "ok", "count": len(apps), "apps": apps}


@router.get("/{app_id}", summary="Get a single registered application")
async def get_app_detail(app_id: str):
    app = await get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return {"status": "ok", "app": app}


@router.delete("/{app_id}", summary="Delete a registered application")
async def remove_app(app_id: str):
    deleted = await delete_app(app_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="App not found")
    return {"status": "ok"}


@router.patch("/{app_id}/status", summary="Enable or disable an application")
async def update_app_status(app_id: str, is_active: bool):
    updated = await set_app_active(app_id, is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="App not found")
    return {"status": "ok", "is_active": is_active}
