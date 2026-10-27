from fastapi import APIRouter, Request

from web_app.config.web_config import web_config, web_config_manager
from .response import ResponseCode, ApiResponse

router = APIRouter()

WEB_SECRET_FIELDS = {"auth_token"}
WEB_EDITABLE_FIELDS = {"auth_token"}


def _redacted_web_config() -> dict:
    configured = []
    visible = dict(web_config)

    for field in WEB_SECRET_FIELDS:
        value = visible.get(field, "")
        if value:
            configured.append(field)
        visible[field] = ""

    return {
        "config": visible,
        "secret_fields": sorted(WEB_SECRET_FIELDS),
        "secret_configured": sorted(configured),
    }


@router.get("")
def web_settings():
    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=_redacted_web_config(),
    )


@router.patch("")
async def update_web_settings(request: Request):
    data = await request.json()
    changes = data.get("changes") if isinstance(data, dict) else None
    if not isinstance(changes, dict):
        return ApiResponse(
            code=ResponseCode.BAD_REQUEST,
            message="changes 必须是对象",
        )

    for key, value in changes.items():
        if key not in WEB_EDITABLE_FIELDS:
            return ApiResponse(
                code=ResponseCode.BAD_REQUEST,
                message=f"未知 Web 配置字段: {key}",
            )
        if not isinstance(value, str):
            return ApiResponse(
                code=ResponseCode.BAD_REQUEST,
                message=f"{key} 必须是字符串",
            )

    if changes:
        web_config_manager.update(changes)

    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=_redacted_web_config(),
    )


# 兼容旧调用方；新前端使用 PATCH changes，避免提交脱敏后的空值覆盖真实 Token
@router.post("/save")
async def save_web_settings(request: Request):
    data = await request.json()
    if not isinstance(data, dict):
        return ApiResponse(
            code=ResponseCode.BAD_REQUEST,
            message="Web 配置必须是对象",
        )
    web_config_manager.update(data)
    return ApiResponse(code=ResponseCode.SUCCESS, message="Success")
