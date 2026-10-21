from fastapi import APIRouter, Request

from seseget.config.config_manager import config
from seseget.output.comic import COMIC_PACKAGERS
from seseget.output.video import VIDEO_METADATA_WRITERS
from .response import ResponseCode, ApiResponse

router = APIRouter()


@router.get("")
def settings():
    return ApiResponse(code=ResponseCode.SUCCESS, message="Success", data=config.dict)


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


@router.post("/save")
async def save(request: Request):
    data = await request.json()
    print("data: ", data)

    print("old config: ", config.dict)
    config.update(data)
    print("new config: ", config.dict)

    return ApiResponse(code=ResponseCode.SUCCESS, message="Success")
