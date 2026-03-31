import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.services.database import connect_db, close_db
from app.services.embedding_service import load_index, get_embedding_model
from app.services.ai_service import _load_model as load_gguf_model
from app.middleware.logger import RequestLoggerMiddleware
from app.api import logs, ai
from app.api import endpoints
from app.api import apps, session_auth, stats
from app.api import ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    get_embedding_model()
    load_index()
    load_gguf_model()
    yield
    await close_db()


app = FastAPI(
    title="SystemAssist — AI Log Intelligence Extension",
    description=(
        "Universal, framework-agnostic micro service for log intelligence and "
        "user interaction analysis. Integrate with any system via API key + user_id."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggerMiddleware)

app.include_router(logs.router)
app.include_router(ai.router)
app.include_router(endpoints.router)
app.include_router(apps.router)
app.include_router(session_auth.router)
app.include_router(stats.router)
app.include_router(ws.router)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_ui():
    index = os.path.join(_STATIC_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return {"message": "SystemAssist API is running. See /docs for API reference."}


@app.get("/admin/login", include_in_schema=False)
async def serve_admin_login():
    index = os.path.join(_STATIC_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return {"message": "Admin console not found."}


@app.get("/user", include_in_schema=False)
async def serve_user_ui():
    user_page = os.path.join(_STATIC_DIR, "user.html")
    if os.path.isfile(user_page):
        return FileResponse(user_page)
    return {"message": "User portal not found."}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SystemAssist", "version": "2.0.0"}
