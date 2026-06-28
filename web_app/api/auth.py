import os
import secrets

from fastapi import APIRouter, Request

from web_app.config.web_config import web_config
from .response import ResponseCode, ApiResponse

router = APIRouter()

AUTH_WHITELIST = [
    "/api/auth/verify",
    "/socket.io",
]


def init_auth_token():
    """启动时初始化认证 token"""
    env_token = os.environ.get("SESEGET_AUTH_TOKEN", "").strip()

    if env_token:
        web_config["auth_token"] = env_token
        return env_token

    config_token = web_config.get("auth_token", "")
    if config_token:
        return config_token

    token = secrets.token_urlsafe(16)
    web_config["auth_token"] = token
    return token


def get_stored_token() -> str:
    """从 web 配置中读取认证 token"""
    return web_config.get("auth_token", "")


def check_token(client_token: str) -> bool:
    """校验客户端 token 是否匹配"""
    stored = get_stored_token()
    if not stored:
        return True
    return client_token == stored


init_auth_token()


@router.post("/verify")
async def verify(request: Request):
    """验证用户输入的 token 是否匹配"""
    data = await request.json() or {}
    user_token = data.get("token", "")

    if not get_stored_token():
        return ApiResponse(
            code=ResponseCode.SERVER_ERROR,
            message="Server token not configured",
        )

    if user_token and check_token(user_token):
        return ApiResponse(
            code=ResponseCode.SUCCESS,
            message="Token verified",
        )

    return ApiResponse(
        code=ResponseCode.UNAUTHORIZED, message="Invalid token", status_code=200
    )
