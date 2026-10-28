"""请求层统一异常。"""

from __future__ import annotations

from typing import Optional


class RequestError(Exception):
    """请求失败的基础异常。"""

    def __init__(
        self,
        message: str,
        *,
        method: str = "",
        url: str = "",
        attempts: int = 1,
        status_code: Optional[int] = None,
        body_preview: str = "",
        cause: Optional[BaseException] = None,
    ) -> None:
        self.method = method
        self.url = url
        self.attempts = attempts
        self.status_code = status_code
        self.body_preview = body_preview
        self.cause = cause
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause


class RequestTimeout(RequestError):
    """连接或读取超时。"""


class RequestConnectionError(RequestError):
    """网络连接失败。"""


class RequestHTTPError(RequestError):
    """上游返回非成功 HTTP 状态。"""

    def __init__(self, message: str, *, retryable: bool = False, **kwargs):
        self.retryable = retryable
        super().__init__(message, **kwargs)


class RequestParseError(RequestError):
    """响应内容无法解析为预期格式。"""


class SiteError(Exception):
    """站点业务错误：请求已成功，但页面内容无法使用。"""

    def __init__(
        self,
        message: str,
        *,
        site: str = "",
        url: str = "",
        cause: Optional[BaseException] = None,
    ) -> None:
        self.site = site
        self.url = url
        self.cause = cause
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause


class SiteAccessError(SiteError):
    """站点拒绝访问：登录/Cookie 失效、反爬或权限限制。"""


class SiteParseError(SiteError):
    """站点返回了内容，但关键页面结构无法解析。"""


class SiteUnsupportedError(SiteError):
    """站点或内容类型不受支持。"""
