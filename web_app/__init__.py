import asyncio
import logging
import os
from contextlib import asynccontextmanager

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import socketio

logger = logging.getLogger(__name__)


# --- 后台任务生命周期 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    from .api.download import emit_download_status

    status_task = asyncio.create_task(emit_download_status())
    logger.info("Download status emitter started")
    yield
    status_task.cancel()
    try:
        await status_task
    except asyncio.CancelledError:
        pass
    logger.info("Download status emitter stopped")


sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI(lifespan=lifespan)


from .api.auth import AUTH_WHITELIST, get_stored_token, check_token
from .api.response import ApiResponse


# --- Auth 中间件 ---
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # 跳过非 API 请求
    if not path.startswith("/api/"):
        return await call_next(request)

    # 跳过白名单
    for allowed in AUTH_WHITELIST:
        if path.startswith(allowed):
            return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return ApiResponse(code=401, message="Missing Authorization header")

    client_token = auth_header[7:] if auth_header.startswith("Bearer ") else auth_header

    if not check_token(client_token):
        return ApiResponse(code=401, message="Invalid token")

    return await call_next(request)


# --- Socket.IO 连接认证 ---
@sio.event
async def connect(sid, environ, auth):
    """Socket.IO 连接时校验 token"""
    stored = get_stored_token()
    if not stored:
        return True
    token = auth.get("token", "") if auth else ""
    if token == stored:
        return True
    raise ConnectionRefusedError("Invalid token")


# --- API 路由 ---
from .api import api_router

app.include_router(api_router, prefix="/api")


# --- 静态文件 ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
assets_dir = os.path.join(static_dir, "assets")
files_dir = os.path.join(static_dir, "files")
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
if os.path.isdir(files_dir):
    app.mount("/static/files", StaticFiles(directory=files_dir), name="static_files")


# --- index.html ---
@app.get("/")
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return ApiResponse(code=404, message="Frontend not built")


# --- 未匹配的其它路由 ---
@app.get("/{path:path}")
async def serve_static(path: str):
    if path.startswith("api/"):
        return ApiResponse(code=404, message="Not Found")

    static_file = os.path.join(static_dir, path)
    if os.path.exists(static_file) and os.path.isfile(static_file):
        return FileResponse(static_file)

    return ApiResponse(code=404, message="Not Found")


# --- Socket.IO 包装 FastAPI ---
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
