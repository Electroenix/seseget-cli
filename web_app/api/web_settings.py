from fastapi import APIRouter, Request

from web_app.config.web_config import web_config
from .response import ResponseCode, ApiResponse

router = APIRouter()


@router.get("")
def web_settings():
    return ApiResponse(
        code=ResponseCode.SUCCESS, message="Success", data=web_config.dict
    )


@router.post("/save")
async def save_web_settings(request: Request):
    data = await request.json()
    web_config.update(data)
    return ApiResponse(code=ResponseCode.SUCCESS, message="Success")
