import asyncio

from curl_cffi import requests as sync_requests
from curl_cffi.requests import AsyncSession
from urllib.parse import urlparse
from urllib.request import getproxies
from typing import Dict
from requests.structures import CaseInsensitiveDict

from ..config import settings
from ..utils.trace import logger
from ..config.config_manager import config


REQUEST_RETRY_MAX = 3
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
            proxy_config = config["common"]["proxy"]
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
            proxy_config = config["common"]["proxy"]
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
async def async_request(method, url, **kwargs):
    """
    发送异步请求
    Args:
        method: 请求方法
        url: 请求地址
        **kwargs: 附加参数

    Returns: 响应对象
    """
    retry_times = 0
    response = None

    while True:
        try:
            response = await session_manager.request(method, url, **kwargs)
            logger.debug(f'request headers: {response.request.headers}')
            break
        except Exception as result:
            if retry_times < REQUEST_RETRY_MAX:
                logger.error('Error! info: %s' % result)
                logger.info("GET %s Failed, Retry(%d)..." % (url, retry_times))
                retry_times = retry_times + 1
                await asyncio.sleep(1)
                continue
            else:
                logger.error('Error! retry max - %d!' % REQUEST_RETRY_MAX)
                break

    return response
