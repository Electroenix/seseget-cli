from fastapi import APIRouter, Request

from seseget.config.config_manager import config
from .response import ResponseCode, ApiResponse

router = APIRouter()


@router.get("")
def settings():
    return ApiResponse(code=ResponseCode.SUCCESS, message="Success", data=config.dict)


@router.post("/save")
async def save(request: Request):
    data = await request.json()
    print("data: ", data)

    print("old config: ", config.dict)
    config.update(data)
    print("new config: ", config.dict)

    return ApiResponse(code=ResponseCode.SUCCESS, message="Success")
