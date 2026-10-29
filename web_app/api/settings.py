from fastapi import APIRouter, Request

from seseget.config.config_manager import config_manager
from seseget.config.schema import (
    build_patch,
    get_ui_schema,
    redact_config,
    validate_changes,
)
from seseget.output.comic import COMIC_PACKAGERS
from seseget.output.video import VIDEO_METADATA_WRITERS

from .response import ApiResponse, ResponseCode

router: APIRouter = APIRouter()


def _settings_payload():
    visible, secret_fields, secret_configured = redact_config(config_manager.data)
    return {
        "config": visible,
        "secret_fields": secret_fields,
        "secret_configured": secret_configured,
    }


@router.get("")
def settings():
    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=_settings_payload(),
    )


@router.get("/schema")
def config_schema():
    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=get_ui_schema(),
    )


@router.patch("")
async def update_settings(request: Request):
    data = await request.json()
    changes = data.get("changes") if isinstance(data, dict) else None
    error = validate_changes(config_manager.data, changes)
    if error:
        return ApiResponse(
            code=ResponseCode.BAD_REQUEST,
            message=error,
        )

    if changes:
        try:
            config_manager.update(build_patch(changes))
        except Exception as e:
            return ApiResponse(
                code=ResponseCode.SERVER_ERROR,
                message=f"保存配置失败: {e}",
            )

    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=_settings_payload(),
    )


@router.get("/formats")
def format_options():
    """返回配置面板中可选的元数据/漫画格式。"""
    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data={
            "download.video.metadata_file": sorted(VIDEO_METADATA_WRITERS),
            "download.comic.format": sorted(COMIC_PACKAGERS),
        },
    )
