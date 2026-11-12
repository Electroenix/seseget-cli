"""站点抓取器与注册器。"""

from typing import Dict, Optional, Type

from ...utils.trace import logger
from .base import AbstractFetcher, SSGBaseFetcher
from .comic import ComicFetcher
from .info import ChapterInfo, ComicInfo, VideoInfo, VideoInfoCache, make_source_info_file
from .video import VideoFetcher

__all__ = [
    "AbstractFetcher",
    "SSGBaseFetcher",
    "FetcherRegistry",
    "ChapterInfo",
    "ComicInfo",
    "VideoInfo",
    "VideoInfoCache",
    "make_source_info_file",
    "ComicFetcher",
    "VideoFetcher",
]


class FetcherRegistry:
    """Fetcher类注册器"""
    _registry: Dict[str, Type[AbstractFetcher]] = {}
    _site_names: Dict[str, str] = {}
    _fetchers: Dict[str, AbstractFetcher] = {}

    @classmethod
    def register(cls, site_key: str, site_name: str = ""):
        """注册装饰器；site_key 用于请求，site_name 用于展示。"""
        def decorator(fetcher_class: Type[AbstractFetcher]):
            if not issubclass(fetcher_class, AbstractFetcher):
                raise TypeError(f"{fetcher_class} 必须继承自 AbstractFetcher")
            cls._registry[site_key] = fetcher_class
            cls._site_names[site_key] = site_name or site_key
            fetcher_class.site_key = site_key
            logger.debug(f"注册Fetcher类{fetcher_class}")
            return fetcher_class
        return decorator

    @classmethod
    def get_fetcher(cls, site_name: str, *args, **kwargs) -> Optional[AbstractFetcher]:
        """获取指定站点的下载器实例"""
        fetcher_class = cls._registry.get(site_name)
        if not fetcher_class:
            raise ValueError(f"未注册的站点: {site_name}")

        fetcher = cls._fetchers.get(site_name)
        if fetcher:
            return fetcher
        else:
            fetcher = fetcher_class(*args, **kwargs)
            cls._fetchers[site_name] = fetcher
            return fetcher

    @classmethod
    def list_sites(cls) -> list:
        """获取所有已注册站点的 key。"""
        return list(cls._registry.keys())

    @classmethod
    def list_site_info(cls) -> list[dict[str, str]]:
        """获取站点 key 和展示名称。"""
        return [
            {"key": key, "name": cls._site_names.get(key, key)}
            for key in cls._registry
        ]

    @classmethod
    def discover(cls, package_name: str):
        """自动发现并注册所有站点实现"""
        import importlib
        import pkgutil
        package = importlib.import_module(package_name)

        for _, module_name, _is_pkg in pkgutil.iter_modules(package.__path__):
            try:
                full_module_name = f"{package_name}.{module_name}"
                importlib.import_module(full_module_name)
            except ImportError as e:
                logger.error("注册站点异常 %s: %s", module_name, e)
