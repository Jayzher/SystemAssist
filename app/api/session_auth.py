from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.models.session import CreateUserSessionRequest
from app.security.rbac import verify_app_api_key
from app.services.user_session_service import (
    create_user_session,
    get_user_session,
    extend_user_session,
    invalidate_user_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _extract_hostname(url: str) -> str:
    try:
        parsed = urlparse(url)
        return (parsed.netloc or parsed.path).lower()
    except Exception:
        return url.lower()


def _domain_matches(request_origin: str, allowed_domain: str) -> bool:
    req_host = _extract_hostname(request_origin)
    allowed = allowed_domain.lower()
    return req_host == allowed or req_host.endswith("." + allowed)


@router.post(
    "/session",
    summary="Create a user session token (called by registered SystemApp on user auth)",
)
async def create_session(
    req: CreateUserSessionRequest,
    request: Request,
    app: dict = Depends(verify_app_api_key),
):
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if origin:
        if not _domain_matches(origin, app["allowed_domain"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Request origin '{_extract_hostname(origin)}' is not authorised "
                    f"for this API key. Allowed domain: '{app['allowed_domain']}'."
                ),
            )

    session = await create_user_session(
        user_id=req.user_id,
        app_id=app["app_id"],
        app_name=app["name"],
        metadata=req.metadata or {},
    )
    return {
        "status": "ok",
        "session_token": session.session_token,
        "user_id": session.user_id,
        "app_id": session.app_id,
        "app_name": session.app_name,
        "expires_at": session.expires_at.isoformat(),
        "created_at": session.created_at.isoformat(),
    }


@router.post(
    "/session/extend",
    summary="Extend a session's TTL (heartbeat — call while the user is active)",
)
async def extend_session(request: Request):
    token = request.headers.get("x-session-token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-Session-Token header required")
    extended = await extend_user_session(token)
    if not extended:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or already expired",
        )
    return {"status": "ok", "extended": True}


@router.get(
    "/session",
    summary="Validate a session token and return session info",
)
async def validate_session(request: Request):
    token = request.headers.get("x-session-token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-Session-Token header required")
    session = await get_user_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
    return {
        "status": "ok",
        "valid": True,
        "user_id": session["user_id"],
        "app_id": session["app_id"],
        "app_name": session["app_name"],
        "expires_at": session["expires_at"].isoformat() if hasattr(session["expires_at"], "isoformat") else session["expires_at"],
        "last_active_at": session["last_active_at"].isoformat() if hasattr(session["last_active_at"], "isoformat") else session["last_active_at"],
    }


@router.delete(
    "/session",
    summary="Invalidate (logout) a session token",
)
async def logout_session(request: Request):
    token = request.headers.get("x-session-token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-Session-Token header required")
    await invalidate_user_session(token)
    return {"status": "ok", "message": "Session invalidated"}
