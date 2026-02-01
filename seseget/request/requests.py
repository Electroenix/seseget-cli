import time
import threading

from curl_cffi import requests
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


class SessionManager:
    """智能 Session 管理器，按请求主机自动分配独立 Session"""

    def __init__(self):
        # 存储不同主机的 Session 对象 {host: Session}
        self._sessions: Dict[str, requests.Session] = {}
        self._lock = threading.Lock()

    def _get_session_for_host(self, host: str) -> requests.Session:
        """获取或创建指定主机的 Session"""
        with self._lock:
            if host not in self._sessions:
                # 创建新 Session 并应用配置
                session = requests.Session()

                self._sessions[host] = session
            # logger.info(f"当前session列表：{list(self._sessions.keys())}")
            return self._sessions[host]

    def request(self, method: requests.HttpMethod, url: str, **kwargs) -> requests.Response:
        """发起请求，自动路由到对应主机的 Session"""
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
        host = parsed_url.netloc  # 提取主机名（如 'api.example.com'）
        session = self._get_session_for_host(host)

        return session.request(method, url, **kwargs)

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def close_all(self):
        """关闭所有 Session 释放资源"""
        with self._lock:
            for host, session in self._sessions.items():
                session.close()
                logger.debug(f"释放Session: {host}")
            self._sessions.clear()


session_manager = SessionManager()


def request(method, url, **kwargs):
    """
    发送请求
    Args:
        method: 请求方法
        url: 请求地址
        **kwargs: 附加参数，将传递给实际发送请求的函数

    Returns: 响应对象

    """
    retry_times = 0
    response = None

    while True:
        try:
            response = session_manager.request(method, url, **kwargs)
            logger.debug(f'request headers: {response.request.headers}')
            break
        except Exception as result:
            if retry_times < REQUEST_RETRY_MAX:
                logger.error('Error! info: %s' % result)
                logger.info("GET %s Failed, Retry(%d)..." % (url, retry_times))
                retry_times = retry_times + 1
                time.sleep(1)
                continue
            else:
                logger.error('Error! retry max - %d!' % REQUEST_RETRY_MAX)
                break

    return response
