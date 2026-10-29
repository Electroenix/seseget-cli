from fastapi import APIRouter

from seseget import __version__

from .response import ApiResponse, ResponseCode

router: APIRouter = APIRouter()


@router.get("")
def version():
    return ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data={"version": __version__},
    )
