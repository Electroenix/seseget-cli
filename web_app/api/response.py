"""API 响应模型"""

from enum import IntEnum

from fastapi.responses import JSONResponse


class ResponseCode(IntEnum):
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500


class ApiResponse(JSONResponse):
    """通用 API 响应"""

    def __init__(
        self,
        code: int = 200,
        message: str = "",
        data=None,
        status_code: int | None = None,
        **kwargs
    ):
        content = {
            "code": code,
            "message": message,
            "data": data if data is not None else {},
        }
        super().__init__(
            content=content,
            status_code=status_code if status_code is not None else code,
            **kwargs,
        )
