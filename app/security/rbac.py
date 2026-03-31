from typing import Optional
from fastapi import Header, HTTPException, Request, status
from app.config import settings


async def verify_api_key(x_api_key: str = Header(..., description="Master API key for admin operations")):
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key


async def verify_app_api_key(x_app_api_key: str = Header(..., description="Per-app API key issued at app registration")):
    from app.services.app_service import get_app_by_api_key
    app = await get_app_by_api_key(x_app_api_key)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive app API key",
        )
    return app


async def get_user_context(
    request: Request,
    x_api_key: Optional[str] = Header(None, description="Master API key (admin / testing)"),
    x_session_token: Optional[str] = Header(None, description="User session token issued after app-level auth"),
) -> dict:
    if x_session_token:
        from app.services.user_session_service import get_user_session, extend_user_session
        session = await get_user_session(x_session_token)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token. Please re-authenticate.",
            )
        await extend_user_session(x_session_token)
        return {
            "user_id": session["user_id"],
            "auth_type": "session_token",
            "session": session,
        }
    if x_api_key:
        if x_api_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        return {"user_id": None, "auth_type": "api_key", "session": None}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide X-Session-Token or X-Api-Key header.",
    )
