import asyncio
import os
import shutil
import sys
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Dict, Generic, Optional, Type, TypeVar, Union

from ..config.config_manager import config
from ..metadata.comic import ComicMetaData
from ..metadata.video import VideoMetaData
from ..output.comic import comic_missing_formats, package_comic
from ..output.video import make_video_metadata_file
from ..utils.file_utils import make_diff_dir_name, make_filename_valid
from ..utils.trace import logger
from . import downloader, task_downloader
from .downloadtask import DownloadTask, FileDLProgress, download_manager
from .errors import RequestError, SiteError, SiteParseError


class ChapterInfo:
    """漫画章节信息，存储章节名，章节号以及漫画元数据"""
    def __init__(self):
        self.title = ""  # 章节名
        self.id = 0
        self.metadata = ComicMetaData()
        self.image_urls: list[str] = []     # 漫画图片url列表
        self.comic_info: ComicInfo | None = None   # 所属的ComicInfo对象, 下载时会引用，务必赋值


class ComicInfo:
    """完整的整部漫画的信息，包含系列名，作者，以及全部章节信息"""
    def __init__(self):
        self.view_url = ""
        self.cid = ""
        self.cover_url = ""
        self.title = ""  # 系列名
        self.author = ""  # 作者
        self.genres = []  # 标签
        self.description = ""
        self.chapter_list: list[ChapterInfo] = []  # 漫画列表，可能有多个章节，以列表形式存储
        self.comic_dir = ""     # 本地保存目录

    def print_info(self):
        logger.info("---------------------------------")
        logger.info(f"cid: {self.cid}")
        logger.info(f"系列: {self.title}")
        logger.info(f"作者: {self.author}")
        logger.info(f"标签: {self.genres}")
        logger.info(f"简介: {self.description}")
        logger.info(f"已获取章节数: {len(self.chapter_list)}")
        logger.info("---------------------------------")


class VideoInfo:
    def __init__(self):
        self.vid = ""
        self.name = ""              # 视频标题
        self.view_url = ""          # 网页地址
        self.download_url = ""      # 下载地址
        self.cover_url = ""         # 封面地址
        self.thumbnail_url = ""     # 缩略图地址
        self.metadata = VideoMetaData()     # 元数据
        self.series_info = []       # 系列视频信息
        self.video_dir = ""         # 本地保存目录

    def print_info(self):
        logger.info("---------------------------------")
        logger.info(f"标题: {self.name}")
        logger.info(f"作者: {self.metadata.author}")
        logger.info(f"标签: {self.metadata.tag_list}")
        logger.info(f"简介: {self.metadata.describe}")
        logger.info(f"封面: {self.cover_url}")
        logger.info("---------------------------------")


class VideoInfoCache:
    def __init__(self, max_size=10):
        self.cache = OrderedDict()
        self.max_size = max_size
        self._lock = asyncio.Lock()

    def get_video_info(self, vid):
        if vid in self.cache:
            self.cache.move_to_end(vid)
            return self.cache[vid]
        return None

    async def update_cache(self, vid, video_info):
        async with self._lock:
            self.cache[vid] = video_info
            if len(self.cache) > self.max_size:
                oldest_vid, _ = self.cache.popitem(last=False)


def make_source_info_file(save_dir, resource_info):
    """创建保存下载资源的来源信息的文件"""
    if config["download"]["save_source_info"]:
        content = ""
        if isinstance(resource_info, VideoInfo):
            content = content + 'video url: %s\r\n' % resource_info.view_url
            content = content + 'thumbnail url: %s\r\n' % resource_info.thumbnail_url
            content = content + 'cover url: %s\r\n' % resource_info.cover_url
            content = content + 'download url: %s\r\n' % resource_info.download_url
        elif isinstance(resource_info, ComicInfo):
            content = "comic url: %s\r\n" % resource_info.view_url
        elif isinstance(resource_info, str):
            content = resource_info
        else:
            logger.warning("Invalid resource_info!")
            return

        with open(save_dir + '/' + 'source.txt', 'wb') as f:
            f.write(content.encode())


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


# 视频站点的抓取器需要继承 VideoFetcher
class VideoFetcher(SSGBaseFetcher[T_VideoInfo], Generic[T_VideoInfo]):
    """视频抓取器基类

    下载任务由两层组成：
    - download(): 抓取 Info，创建任务并设置 runner；
    - _download_task(): 任务 runner，负责目录、元数据、source 和媒体下载。

    子类通常只需要重写：
    - _fetch_info
    - _prepare_dir（站点特殊的保存路径）
    - _write_outputs（站点特殊的元数据）
    - _build_source_info（source.txt 内容）
    - _download_media（merge/yt-dlp 等特殊下载方式）
    """

    def __init__(self, max_tasks=5):
        super().__init__(max_tasks)
        self.video_info_cache = VideoInfoCache(10)
        self._dir_lock = asyncio.Lock()

    def _prepare_dir(self, info: T_VideoInfo):
        if not self.__class__.site_dir:
            raise ValueError("未指定下载目录!")
        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)

        series_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.metadata.series))
        info.video_dir = os.path.join(series_dir, make_filename_valid(info.name))
        info.video_dir = make_diff_dir_name(info.video_dir)

        if not os.path.exists(series_dir):
            os.mkdir(series_dir)
        if not os.path.exists(info.video_dir):
            os.mkdir(info.video_dir)

    def _build_source_info(self, info: T_VideoInfo) -> str:
        content = 'video url: %s\r\n' % info.view_url
        content = content + 'thumbnail url: %s\r\n' % info.thumbnail_url
        content = content + 'cover url: %s\r\n' % info.cover_url
        content = content + 'download url: %s\r\n' % info.download_url
        return content

    async def _write_outputs(self, task: DownloadTask, info: T_VideoInfo):
        result = 0
        poster_path = ""
        fanart_path = ""

        if info.cover_url:
            poster_path = info.video_dir + '/' + 'poster.jpg'
            result = await downloader.download_file(poster_path, info.cover_url)
        if info.thumbnail_url:
            fanart_path = info.video_dir + '/' + 'fanart.jpg'
            result = result | await downloader.download_file(fanart_path, info.thumbnail_url)

        if result == 0:
            info.metadata.describe = info.metadata.describe + '\r\n%s' % info.view_url
            info.metadata.back_ground_path = fanart_path
            make_video_metadata_file(info.video_dir, info.name, info.metadata)

        make_source_info_file(info.video_dir, self._build_source_info(info))

    async def _download_media(self, task: DownloadTask, info: T_VideoInfo):
        video_path = info.video_dir + '/' + make_filename_valid('%s.mp4' % info.name)

        if '.m3u8' in info.download_url.split('/')[-1]:
            await task_downloader.download_mp4_by_m3u8(task, video_path, info.download_url)
        else:
            await task_downloader.download_mp4(task, video_path, info.download_url)

    async def _download_task(self, task: DownloadTask, info: T_VideoInfo):
        async with self._dir_lock:
            self._prepare_dir(info)

        task.track_dir(info.video_dir)
        task.task_progress.set_status(FileDLProgress.Status.PROCESS)
        try:
            await self._write_outputs(task, info)
        except Exception as exc:
            logger.warning("写入视频元数据失败，继续下载: %s", exc)

        task.task_progress.set_status(FileDLProgress.Status.DOWNLOADING)
        await self._download_media(task, info)

    async def download(self, url, **kwargs):
        default_params = {
            "no_download": False,
        }
        params = {**default_params, **kwargs}

        async with self.fetch_semaphore:
            video_info = await self._fetch_info_guarded(url)
        video_info.print_info()

        if params["no_download"]:
            return

        task = download_manager.new_task(video_info.name, site=self.site_key)
        task.set_runner(self._download_task, video_info)
        download_manager.start(task)


# 漫画站点的抓取器需要继承 ComicFetcher
class ComicFetcher(SSGBaseFetcher[T_ComicInfo], Generic[T_ComicInfo, T_ChapterInfo]):
    """漫画抓取器基类

    子类通常只需要重写：
    - _fetch_info
    - _prepare_comic_dir（整部漫画的共享目录）
    - _prepare_chapter / _package / _write_source_info
    - 或直接重写 _download_task（如 jm_comic）
    """

    def __init__(self, max_tasks=1):
        super().__init__(max_tasks=max_tasks)
        self.capter_lock = asyncio.Lock()
        self._dir_lock = asyncio.Lock()

    def _prepare_comic_dir(self, info: T_ComicInfo):
        if not self.__class__.site_dir:
            raise ValueError("未指定下载目录!")
        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)

        # 漫画目录由整部漫画共享，不能避重；章节产物靠章节文件名区分
        comic_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.title))
        if os.path.exists(comic_dir) and not os.path.isdir(comic_dir):
            raise ValueError(f"漫画保存路径已存在且不是目录: {comic_dir}")

        info.comic_dir = comic_dir
        os.makedirs(info.comic_dir, exist_ok=True)

    def _prepare_chapter(self, comic_info: ComicInfo, chapter: T_ChapterInfo) -> str:
        image_dir = f"{comic_info.comic_dir}/img-{chapter.id}"
        os.makedirs(image_dir, exist_ok=True)
        return image_dir

    def _package(self, task: DownloadTask, comic_dir: str, comic_title: str,
                 image_dir: str, chapter: T_ChapterInfo):
        before = set(os.listdir(comic_dir))
        try:
            package_comic(comic_dir, comic_title, image_dir, chapter.metadata)
        finally:
            for name in set(os.listdir(comic_dir)) - before:
                path = os.path.join(comic_dir, name)
                if os.path.isfile(path):
                    task.track_file(path)

    def _write_source_info(self, task: DownloadTask, comic_info: ComicInfo):
        make_source_info_file(comic_info.comic_dir, 'comic url: %s\r\n' % comic_info.view_url)

    async def _download_task(self, task: DownloadTask, comic_title: str, chapter: T_ChapterInfo):
        comic_info = chapter.comic_info
        if comic_info is None:
            raise ValueError("章节缺少所属漫画信息")

        async with self.capter_lock:
            if not comic_missing_formats(comic_info.comic_dir, comic_title):
                logger.warning("漫画成品已存在，跳过下载: %s", comic_title)
                task.task_progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)
                return

            image_dir = self._prepare_chapter(comic_info, chapter)
            task.track_dir(image_dir)
            res = await task_downloader.download_comic_capter_images(
                task, image_dir, chapter.image_urls
            )
            self._package(task, comic_info.comic_dir, comic_title, image_dir, chapter)

            task.task_progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)

            if not config["download"]["comic"]["leave_images"]:
                shutil.rmtree(image_dir)
                logger.info('已删除图片缓存')

            self._write_source_info(task, comic_info)
            return res

    def _chapter_task_name(self, comic_info: T_ComicInfo, chapter: T_ChapterInfo) -> str:
        comic_title = make_filename_valid(comic_info.title + "_%03d" % chapter.id)

        if sys.platform.startswith("win"):
            valid_len = 259 - (len(os.path.abspath(comic_info.comic_dir)) + 1)
            format_max = max(config["download"]["comic"]["format"], key=len, default="")
            if valid_len < len(f'{comic_title}.{format_max}'):
                if valid_len > len(f'{str(chapter.id)}.{format_max}'):
                    comic_title = str(chapter.id)
                else:
                    raise ValueError("当前目标路径过长，无法创建漫画文件")
        return comic_title

    @abstractmethod
    async def _fetch_info(self, url, **kwargs) -> T_ComicInfo:
        """抓取资源信息，子类需要实现该功能"""
        pass

    async def download(self, url, **kwargs):
        default_params = {
            "no_download": False,
            "chapter_id_list": None
        }
        params = {**default_params, **kwargs}

        async with self.fetch_semaphore:
            comic_info = await self._fetch_info_guarded(url, chapter_id_list=params["chapter_id_list"])
        comic_info.print_info()

        if params["no_download"]:
            return

        async with self._dir_lock:
            self._prepare_comic_dir(comic_info)

        for chapter in comic_info.chapter_list:
            comic_title = self._chapter_task_name(comic_info, chapter)
            logger.info("正在下载第%d章" % chapter.id)
            task = download_manager.new_task(comic_title, site=self.site_key)
            task.set_runner(self._download_task, comic_title, chapter)
            download_manager.start(task)


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
