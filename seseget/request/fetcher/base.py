import asyncio
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Union

from ...utils.trace import logger
from ..errors import RequestError, SiteError, SiteParseError
from .info import ChapterInfo, ComicInfo, VideoInfo


class AbstractFetcher(ABC):
    """站点抓取器基类

    所有fecher都应该实现两个方法
    - download 下载资源
    - info 获取元数据信息
    """

    site_key: str = ""

    @abstractmethod
    async def download(self, url, **kwargs):
        pass

    @abstractmethod
    async def info(self, url, **kwargs):
        pass


T_Info = TypeVar('T_Info', bound=Union[VideoInfo, ComicInfo])
T_VideoInfo = TypeVar('T_VideoInfo', bound=VideoInfo)
T_ComicInfo = TypeVar('T_ComicInfo', bound=ComicInfo)
T_ChapterInfo = TypeVar('T_ChapterInfo', bound=ChapterInfo)


class SSGBaseFetcher(AbstractFetcher, Generic[T_Info]):
    """站点抓取器基类

    补充了一些通用方法。
    """

    site_dir = ""

    def __init__(self, max_tasks=5):
        self.max_tasks = max_tasks
        self.fetch_semaphore = asyncio.Semaphore(max_tasks)

    @abstractmethod
    async def _fetch_info(self, url, **kwargs) -> T_Info:
        """抓取资源信息，子类需要实现该功能"""
        pass

    @abstractmethod
    async def download(self, url, **kwargs):
        pass

    async def _fetch_info_guarded(self, url, **kwargs):
        """在统一边界区分请求/站点错误与未预期的解析异常。"""
        try:
            return await self._fetch_info(url, **kwargs)
        except (RequestError, SiteError):
            raise
        except Exception as exc:
            logger.exception(
                "站点解析失败: %s %s", type(self).__name__, url
            )
            raise SiteParseError(
                "站点返回内容无法解析：可能是反爬验证页、登录状态失效、"
                "访问受限或页面结构变化，请检查配置并稍后重试",
                site=type(self).__name__,
                url=url,
                cause=exc,
            ) from exc

    async def info(self, url, **kwargs):
        async with self.fetch_semaphore:
            return await self._fetch_info_guarded(url, **kwargs)
