import asyncio
import os
import sys
import shutil
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Dict, Type, Optional, TypeVar, Generic, Union

from . import downloader
from ..config.config_manager import config
from ..metadata.comic import ComicMetaData
from ..metadata.video import VideoMetaData
from ..metadata.video.doc import make_video_metadata_file
from ..metadata.comic.doc import make_comic
from ..utils.file_utils import make_filename_valid, make_diff_dir_name
from ..utils.trace import logger
from .downloadtask import FileDLProgress, TaskDLProgress, download_manager


class ChapterInfo:
    """漫画章节信息，存储章节名，章节号以及漫画元数据"""
    def __init__(self):
        self.title = ""  # 章节名
        self.id = 0
        self.metadata = ComicMetaData()
        self.image_urls: list[str] = []     # 漫画图片url列表
        self.comic_info: ComicInfo = None   # 所属的ComicInfo对象, 下载时会引用，务必赋值


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
        logger.info(f"---------------------------------")
        logger.info(f"cid: {self.cid}")
        logger.info(f"系列: {self.title}")
        logger.info(f"作者: {self.author}")
        logger.info(f"标签: {self.genres}")
        logger.info(f"简介: {self.description}")
        logger.info(f"已获取章节数: {len(self.chapter_list)}")
        logger.info(f"---------------------------------")


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
        logger.info(f"---------------------------------")
        logger.info(f"标题: {self.name}")
        logger.info(f"作者: {self.metadata.author}")
        logger.info(f"标签: {self.metadata.tag_list}")
        logger.info(f"简介: {self.metadata.describe}")
        logger.info(f"封面: {self.cover_url}")
        logger.info(f"---------------------------------")


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
    
    补充了一些通用方法
    """
    site_dir = ""

    def __init__(self, max_tasks=5):
        self.max_tasks = max_tasks
        self.task_semaphore = asyncio.Semaphore(max_tasks)

    @abstractmethod
    def _make_save_dir(self, info: T_Info):
        pass

    @abstractmethod
    def _make_source_info_file(self, info: T_Info):
        pass

    @abstractmethod
    async def _fetch_info(self, url, **kwargs) -> T_Info:
        """抓取资源信息，子类需要实现该功能"""
        pass

    @abstractmethod
    async def download(self, url, **kwargs):
        pass

    async def info(self, url, **kwargs):
        return await self._fetch_info(url, **kwargs)


# 视频站点的抓取器需要继承VideoFetcher
class VideoFetcher(SSGBaseFetcher[T_VideoInfo], Generic[T_VideoInfo]):
    """视频抓取器基类
    
    已实现如下功能：
    - _make_save_dir 创建保存目录
    - _make_metadata_file 创建元数据文件
    - _make_source_info_file 创建来源信息
    - _download_process 基础的下载流程，通过 VideoInfo 对象中的 url 地址下载
    - _download_process_with_semaphore 控制并发数的下载流程
    - _start_download_task 创建下载任务
    - download 基础的下载接口

    需要实现的功能：
    - _fetch_info 获取站点信息，解析出 T_VideoInfo 信息

    Note:

    如果_download_process中的下载方式无法满足需求，可根据需求重写， 

    T_VideoInfo 可修改为继承自 VideoInfo 的子类型，其它使用 T_VideoInfo 作为参数的函数根据需要重写
    """

    def __init__(self, max_tasks=5):
        super().__init__(max_tasks)
        self.video_info_cache = VideoInfoCache(10)

    def _make_save_dir(self, info: T_Info):
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

    async def _make_metadata_file(self, video_info: T_VideoInfo):
        result = 0
        poster_path = ""
        fanart_path = ""

        if video_info.cover_url:
            poster_path = video_info.video_dir + '/' + 'poster.jpg'
            result = await downloader.download_file(poster_path, video_info.cover_url)
        if video_info.thumbnail_url:
            fanart_path = video_info.video_dir + '/' + 'fanart.jpg'
            result = result | await downloader.download_file(fanart_path, video_info.thumbnail_url)

        if result == 0:
            video_info.metadata.describe = video_info.metadata.describe + '\r\n%s' % video_info.view_url
            video_info.metadata.back_ground_path = fanart_path
            make_video_metadata_file(video_info.video_dir, video_info.name, video_info.metadata)

    def _make_source_info_file(self, info: T_VideoInfo):
        make_source_info_file(info.video_dir, info)

    async def _download_process(self, video_info: T_VideoInfo, progress: TaskDLProgress = None):
        """此处实现了基本的资源下载逻辑，子类可以根据需要选择继承或重写"""
        video_path = video_info.video_dir + '/' + make_filename_valid('%s.mp4' % video_info.name)

        if '.m3u8' in video_info.download_url.split('/')[-1]:
            await downloader.download_mp4_by_m3u8(video_path, video_info.download_url, progress)
        else:
            await downloader.download_mp4(video_path, video_info.download_url, progress)

    async def _download_process_with_semaphore(self, video_info: T_VideoInfo, progress: TaskDLProgress = None):
        try:
            await self._download_process(video_info, progress)
        except Exception:
            raise
        finally:
            self.task_semaphore.release()

    async def _start_download_task(self, video_info: T_VideoInfo):
        await download_manager.create_task(video_info.name, self._download_process_with_semaphore, video_info)

    @abstractmethod
    async def _fetch_info(self, url, **kwargs) -> T_VideoInfo:
        """抓取资源信息，子类需要实现该功能"""
        pass

    async def download(self, url, **kwargs):
        default_params = {
            "no_download": False,
        }
        params = {**default_params, **kwargs}
        await self.task_semaphore.acquire()

        video_info = await self._fetch_info(url)
        video_info.print_info()

        if params["no_download"]:
            self.task_semaphore.release()
            return

        self._make_save_dir(video_info)
        await self._start_download_task(video_info)
        await self._make_metadata_file(video_info)
        self._make_source_info_file(video_info)


# 漫画站点的抓取器需要继承ComicFetcher
class ComicFetcher(SSGBaseFetcher[T_ComicInfo], Generic[T_ComicInfo, T_ChapterInfo]):
    """漫画抓取器基类
    
    已实现如下功能：
    - _make_save_dir 创建保存目录
    - _download_process 基础的下载流程，通过 ChapterInfo 对象中的 chapter.image_urls 地址下载所有图片并合并为漫画文件
    - _download_process_with_semaphore 控制并发数的下载流程
    - _start_download_task 创建下载任务
    - download 基础的下载接口

    需要实现的功能：
    - _fetch_info 获取站点信息，并解析出 T_ComicInfo 中信息

    Note:

    如果_download_process中的下载方式无法满足需求，可根据需求重写， 

    T_ComicInfo 可修改为继承自 ComicInfo 的子类型，
    T_ChapterInfo 可修改为继承自 ChapterInfo 的子类型，
    其它使用 T_ComicInfo 或 T_ChapterInfo 作为参数的函数根据需要重写
    """

    def __init__(self, max_tasks=1):
        super().__init__(max_tasks=max_tasks)
        self.capter_lock = asyncio.Lock()

    def _make_save_dir(self, info: T_Info):
        if not self.__class__.site_dir:
            raise ValueError("未指定下载目录!")
        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)

        info.comic_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.title))
        info.comic_dir = make_diff_dir_name(info.comic_dir)
        if not os.path.exists(info.comic_dir):
            os.mkdir(info.comic_dir)

    async def _download_process(self, comic_title: str, chapter: T_ChapterInfo, progress: TaskDLProgress = None):
        """此处实现了基本的资源下载逻辑，子类可以根据需要选择继承或重写"""
        comic_info = chapter.comic_info
        comic_dir = comic_info.comic_dir

        image_temp_dir_path = f"{comic_dir}/img-{chapter.id}"

        if not os.path.exists(image_temp_dir_path):
            os.mkdir(image_temp_dir_path)

        res = await downloader.download_comic_capter_images(image_temp_dir_path, chapter.image_urls, progress)

        # 图片下载完成，打包成漫画文件
        make_comic(comic_dir, comic_title, image_temp_dir_path, chapter.metadata)

        if progress:
            progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)

        # 删除图片文件夹
        if not config["download"]["comic"]["leave_images"]:
            shutil.rmtree(image_temp_dir_path)
            logger.info('已删除图片缓存')

        return res

    async def _download_process_with_semaphore(self, comic_title: str, chapter: T_ChapterInfo, progress: TaskDLProgress = None):
        try:
            async with self.capter_lock:
                await self._download_process(comic_title, chapter, progress)
        except Exception:
            raise
        finally:
            self.task_semaphore.release()

    async def _start_download_task(self, chapter: T_ChapterInfo):
        comic_info = chapter.comic_info
        comic_title = make_filename_valid(comic_info.title + "_%03d" % chapter.id)

        if sys.platform.startswith("win"):
            valid_len = 259 - (len(os.path.abspath(comic_info.comic_dir)) + 1)
            format_max = max(config["download"]["comic"]["format"], key=len, default="")
            if valid_len < len(f'{comic_title}.{format_max}'):
                if valid_len > len(f'{str(chapter.id)}.{format_max}'):
                    comic_title = str(chapter.id)
                else:
                    raise ValueError("当前目标路径过长，无法创建漫画文件")

        logger.info("正在下载第%d章" % chapter.id)
        task_name = comic_title
        await download_manager.create_task(task_name, self._download_process_with_semaphore, comic_title, chapter)

    def _make_source_info_file(self, info: T_ComicInfo):
        make_source_info_file(info.comic_dir, info)

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
        await self.task_semaphore.acquire()

        comic_info = await self._fetch_info(url, chapter_id_list=params["chapter_id_list"])
        comic_info.print_info()

        if params["no_download"]:
            self.task_semaphore.release()
            return

        self._make_save_dir(comic_info)

        for chapter in comic_info.chapter_list:
            await self._start_download_task(chapter)
            self._make_source_info_file(comic_info)


class FetcherRegistry:
    """Fetcher类注册器"""
    _registry: Dict[str, Type[AbstractFetcher]] = {}
    _fetchers: Dict[str, AbstractFetcher] = {}

    @classmethod
    def register(cls, site_name: str):
        """注册装饰器"""
        def decorator(fetcher_class: Type[AbstractFetcher]):
            if not issubclass(fetcher_class, AbstractFetcher):
                raise TypeError(f"{fetcher_class} 必须继承自 AbstractFetcher")
            cls._registry[site_name] = fetcher_class
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
        """获取所有已注册站点名称"""
        return list(cls._registry.keys())

    @classmethod
    def discover(cls, package_name: str):
        """自动发现并注册所有站点实现"""
        import importlib
        import pkgutil
        package = importlib.import_module(package_name)

        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            try:
                full_module_name = f"{package_name}.{module_name}"
                site_module = importlib.import_module(full_module_name)
            except ImportError as e:
                print(f"注册站点异常 {module_name}: {str(e)}")
