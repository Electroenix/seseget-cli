from fastapi import APIRouter

from seseget import __version__
from .response import ResponseCode, ApiResponse

router = APIRouter()


@router.get("")
def version():
    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data={"version": __version__},
    )
