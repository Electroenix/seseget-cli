import asyncio

from curl_cffi import requests as sync_requests
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
from curl_cffi.requests.exceptions import RequestException as CurlRequestException
from curl_cffi.requests.exceptions import Timeout as CurlTimeout
from urllib.parse import urlparse
from urllib.request import getproxies
from typing import Dict
from requests.structures import CaseInsensitiveDict

from ..config import settings
from ..utils.trace import logger
from ..config.config_manager import config
from .errors import RequestConnectionError, RequestError, RequestHTTPError, RequestTimeout


REQUEST_MAX_ATTEMPTS = 3
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}


# 同步 SessionManager（已废弃，同步请求会阻塞线程，请使用异步请求）
class SessionManager:
    """同步 Session 管理器 """

    def __init__(self):
        import threading
        self._sessions: Dict[str, sync_requests.Session] = {}
        self._lock = threading.Lock()

    def _get_session_for_host(self, host: str) -> sync_requests.Session:
        with self._lock:
            if host not in self._sessions:
                session = sync_requests.Session()
                self._sessions[host] = session
            return self._sessions[host]

    def request(self, method, url, **kwargs) -> sync_requests.Response:
        if "headers" in kwargs:
            headers = CaseInsensitiveDict(DEFAULT_HEADERS)
            headers.update(kwargs["headers"])
            kwargs["headers"] = headers.copy()
        else:
            kwargs["headers"] = DEFAULT_HEADERS.copy()
        logger.debug(f'headers: {kwargs["headers"]}')

        if "proxies" not in kwargs:
            proxy_config = config["network"]["proxy"]
            if proxy_config:
                proxies = {
                    "http": proxy_config,
                    "https": proxy_config,
                }
                kwargs["proxies"] = proxies
            else:
                sys_proxies = getproxies()
                proxies = {
                    "http": sys_proxies.get("http"),
                    "https": sys_proxies.get("https"),
                }
                kwargs["proxies"] = proxies
            logger.debug(f'proxy: {kwargs["proxies"]}')

        if "impersonate" not in kwargs:
            kwargs["impersonate"] = "chrome110"

        if "timeout" not in kwargs:
            kwargs["timeout"] = settings.REQUEST_TIMEOUT

        parsed_url = urlparse(url)
        host = parsed_url.netloc
        session = self._get_session_for_host(host)

        return session.request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def close_all(self):
        with self._lock:
            for host, session in self._sessions.items():
                session.close()
                logger.debug(f"释放Session: {host}")
            self._sessions.clear()


# session_manager = SessionManager()


# 异步 SessionManager
class AsyncSessionManager:
    """异步 Session 管理器，按请求主机自动分配独立 AsyncSession"""

    def __init__(self):
        self._sessions: Dict[str, AsyncSession] = {}
        self._lock = asyncio.Lock()

    async def _get_session_for_host(self, host: str) -> AsyncSession:
        async with self._lock:
            if host not in self._sessions:
                session = AsyncSession()
                self._sessions[host] = session
            return self._sessions[host]

    async def request(self, method, url, **kwargs):
        """发起异步请求，自动路由到对应主机的 AsyncSession"""
        if "headers" in kwargs:
            headers = CaseInsensitiveDict(DEFAULT_HEADERS)
            headers.update(kwargs["headers"])
            kwargs["headers"] = headers.copy()
        else:
            kwargs["headers"] = DEFAULT_HEADERS.copy()
        logger.debug(f'headers: {kwargs["headers"]}')

        if "proxies" not in kwargs:
            proxy_config = config["network"]["proxy"]
            if proxy_config:
                proxies = {
                    "http": proxy_config,
                    "https": proxy_config,
                }
                kwargs["proxies"] = proxies
            else:
                sys_proxies = getproxies()
                proxies = {
                    "http": sys_proxies.get("http"),
                    "https": sys_proxies.get("https"),
                }
                kwargs["proxies"] = proxies
            logger.debug(f'proxy: {kwargs["proxies"]}')

        if "impersonate" not in kwargs:
            kwargs["impersonate"] = "chrome110"

        if "timeout" not in kwargs:
            kwargs["timeout"] = settings.REQUEST_TIMEOUT

        parsed_url = urlparse(url)
        host = parsed_url.netloc
        session = await self._get_session_for_host(host)

        return await session.request(method, url, **kwargs)

    async def get(self, url, **kwargs):
        return await self.request("GET", url, **kwargs)

    async def post(self, url, **kwargs):
        return await self.request("POST", url, **kwargs)

    async def close_all(self):
        async with self._lock:
            for host, session in self._sessions.items():
                await session.close()
                logger.debug(f"释放AsyncSession: {host}")
            self._sessions.clear()


session_manager = AsyncSessionManager()


# 请求接口
async def async_request(method: str, url: str, **kwargs):
    """发送异步请求，成功返回 2xx response，失败抛出 RequestError 子类。

    超时、连接失败和可重试的 HTTP 状态会重试；其余 4xx 立即失败。
    """
    last_error = None

    for attempt in range(1, REQUEST_MAX_ATTEMPTS + 1):
        response = None
        try:
            response = await session_manager.request(method, url, **kwargs)
        except CurlTimeout as exc:
            last_error = RequestTimeout(
                f"{method} {url} 请求超时 (尝试 {attempt} 次)",
                method=method,
                url=url,
                attempts=attempt,
                cause=exc,
            )
        except (CurlConnectionError, CurlRequestException) as exc:
            last_error = RequestConnectionError(
                f"{method} {url} 网络请求失败 (尝试 {attempt} 次): {exc}",
                method=method,
                url=url,
                attempts=attempt,
                cause=exc,
            )
        except Exception:
            # 非请求库异常不应被重试逻辑吞掉
            raise
        else:
            status_code = response.status_code
            if 200 <= status_code < 300:
                return response

            body_preview = ""
            try:
                body_preview = response.text[:200].strip()
            except Exception:
                pass

            last_error = RequestHTTPError(
                f"{method} {url} 返回 HTTP {status_code}",
                method=method,
                url=url,
                attempts=attempt,
                status_code=status_code,
                body_preview=body_preview,
                retryable=status_code in RETRYABLE_STATUS,
            )
            response.close()

        if isinstance(last_error, RequestHTTPError) and not last_error.retryable:
            raise last_error

        if attempt >= REQUEST_MAX_ATTEMPTS:
            raise last_error

        logger.warning(
            "%s，%s 后重试 (%d/%d)",
            last_error,
            "1s",
            attempt,
            REQUEST_MAX_ATTEMPTS,
        )
        await asyncio.sleep(1)

    # 理论不可达；保证类型检查不会推断返回 None
    assert last_error is not None
    raise last_error
