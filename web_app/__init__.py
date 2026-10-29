import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

import socketio

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from seseget.config import settings

settings.PROGRESS_BAR_ENABLED = False
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


from seseget.request.errors import (
    RequestError,
    RequestHTTPError,
    RequestTimeout,
    SiteError,
    SiteUnsupportedError,
)

from .api.auth import AUTH_WHITELIST, check_token, get_stored_token
from .api.response import ApiResponse, ResponseCode


# --- 未预期异常兜底 ---
@app.middleware("http")
async def unhandled_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled API error on %s: %s", request.url.path, exc)
        return ApiResponse(
            code=ResponseCode.SERVER_ERROR,
            message="服务器内部错误",
        )


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
@app.exception_handler(RequestError)
async def request_error_handler(request: Request, exc: RequestError):
    """把请求层异常转换成统一的 JSON 错误响应。"""
    logger.warning("Request failed: %s", exc)
    code = (
        ResponseCode.GATEWAY_TIMEOUT
        if isinstance(exc, RequestTimeout)
        else ResponseCode.BAD_GATEWAY
    )
    message = str(exc)
    if isinstance(exc, RequestHTTPError) and exc.status_code in (401, 403, 429):
        message = (
            f"{message}；可能为 Cookie 失效、登录过期或触发反爬验证，"
            "请检查配置后重试"
        )
    return ApiResponse(code=code, message=message)


@app.exception_handler(SiteError)
async def site_error_handler(request: Request, exc: SiteError):
    """把站点解析/访问错误转换成带可读消息的 JSON 响应。"""
    logger.warning("Site error: %s", exc)
    code = (
        ResponseCode.BAD_REQUEST
        if isinstance(exc, SiteUnsupportedError)
        else ResponseCode.BAD_GATEWAY
    )
    return ApiResponse(code=code, message=str(exc))


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
