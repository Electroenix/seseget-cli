from flask import request, Blueprint
from web_app.config.web_config import web_config
from .response import ResponseCode, ApiResponse

auth_bp = Blueprint('api/auth', __name__)


def _get_stored_token() -> str:
    """从 web 配置中读取认证 token"""
    return web_config.get('auth_token', '')


@auth_bp.route('/verify', methods=['POST'])
def verify():
    """验证用户输入的 token 是否匹配"""
    data = request.get_json(silent=True) or {}
    user_token = data.get('token', '')
    stored_token = _get_stored_token()

    if not stored_token:
        return ApiResponse(
            code=ResponseCode.SERVER_ERROR,
            message="Server token not configured"
        ).to_response()

    if user_token and user_token == stored_token:
        return ApiResponse(
            code=ResponseCode.SUCCESS,
            message="Token verified"
        ).to_response()
    else:
        return ApiResponse(
            code=ResponseCode.UNAUTHORIZED,
            message="Invalid token"
        ).to_response()


# 不需要认证的 API 路径白名单
_AUTH_WHITELIST = [
    '/api/auth/verify',
    '/socket.io',
]


def check_auth() -> None:
    """全局认证中间件 — 检查 API 请求的 Authorization header"""
    path = request.path

    # 跳过非 API 请求
    if not path.startswith('/api/'):
        return

    # 跳过白名单
    for allowed in _AUTH_WHITELIST:
        if path.startswith(allowed):
            return

    stored_token = _get_stored_token()
    if not stored_token:
        # 未配置 token 则放行（向后兼容）
        return

    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return ApiResponse(
            code=ResponseCode.UNAUTHORIZED,
            message="Missing Authorization header"
        ).to_response(), 401

    # 支持 Bearer token
    if auth_header.startswith('Bearer '):
        client_token = auth_header[7:]
    else:
        client_token = auth_header

    if client_token != stored_token:
        return ApiResponse(
            code=ResponseCode.UNAUTHORIZED,
            message="Invalid token"
        ).to_response(), 401
