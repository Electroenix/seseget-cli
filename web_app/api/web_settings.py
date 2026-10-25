from fastapi import APIRouter, Request

from web_app.config.web_config import web_config, web_config_manager
from .response import ResponseCode, ApiResponse

router = APIRouter()


@router.get("")
def web_settings():
    return ApiResponse(
        code=ResponseCode.SUCCESS, message="Success", data=web_config
    )


@router.post("/save")
async def save_web_settings(request: Request):
    data = await request.json()
    web_config_manager.update(data)
    return ApiResponse(code=ResponseCode.SUCCESS, message="Success")
