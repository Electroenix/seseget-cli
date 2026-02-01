import os
import sys
import threading
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
        self.cache = OrderedDict()  # 核心缓存容器
        self.max_size = max_size  # 最大缓存数量

    def get_video_info(self, vid):
        """ 获取视频信息（自动缓存） """
        if vid in self.cache:
            # 命中缓存：移动元素到末尾表示最近使用
            self.cache.move_to_end(vid)
            #PRINTLOG(f"缓存命中 vid: {vid}")
            return self.cache[vid]

        # 缓存未命中
        return None

    def update_cache(self, vid, video_info):
        """ 更新缓存并执行淘汰策略 """
        self.cache[vid] = video_info
        if len(self.cache) > self.max_size:
            # 移除最久未使用的条目
            oldest_vid, _ = self.cache.popitem(last=False)
            #PRINTLOG(f"移除过期缓存 vid: {oldest_vid}")
        #PRINTLOG("当前缓存:", list(self.cache.keys()))


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
    """站点抓取器基类"""

    @abstractmethod
    def download(self, url, **kwargs):
        """
        实现资源下载的完整流程，包括抓取信息，下载和文件处理
        Args:
            url: 请求资源地址
            **kwargs: 可选配置参数

        """
        pass

    @abstractmethod
    def info(self, url, **kwargs):
        pass


T_Info = TypeVar('T_Info', bound=Union[VideoInfo, ComicInfo])
T_VideoInfo = TypeVar('T_VideoInfo', bound=VideoInfo)
T_ComicInfo = TypeVar('T_ComicInfo', bound=ComicInfo)
T_ChapterInfo = TypeVar('T_ChapterInfo', bound=ChapterInfo)


class SSGBaseFetcher(AbstractFetcher, Generic[T_Info]):
    site_dir = ""  # 站点目录，需要在子类中指定目录

    def __init__(self, max_tasks=5):
        self.max_tasks = max_tasks
        self.task_semaphore = threading.Semaphore(max_tasks)

    @abstractmethod
    def _make_save_dir(self, info: T_Info):
        pass

    @abstractmethod
    def _make_source_info_file(self, info: T_Info):
        pass

    @abstractmethod
    def _fetch_info(self, url, **kwargs) -> T_Info:
        """抓取资源信息，子类需要实现该功能"""
        pass

    @abstractmethod
    def download(self, url, **kwargs):
        pass

    def info(self, url, **kwargs):
        return self._fetch_info(url, **kwargs)


class VideoFetcher(SSGBaseFetcher[T_VideoInfo], Generic[T_VideoInfo]):
    """视频抓取器基类，已实现视频下载标准流程，子类需要实现get_info函数获取必须的视频信息"""

    def __init__(self, max_tasks=5):
        super().__init__(max_tasks)
        self.video_info_cache = VideoInfoCache(10)

    def _make_save_dir(self, info: T_Info):
        # 视频下载目录说明
        # data  # 下载目录
        # └── site  # 站点目录
        #     └── series  # 系列目录
        #         └── video  # 视频目录
        #             ├── video.mp4  # 视频文件
        #             ├── video.nfo  # 元数据文件
        #             ├── fanart.jpg  # 背景图片
        #             ├── poster.jpg  # 封面图片
        #             └── source.txt  # 下载来源信息
        if not self.__class__.site_dir:
            raise ValueError("未指定下载目录!")
        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)

        series_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.metadata.series))  # 中间目录，系列作品放在同一目录下
        info.video_dir = os.path.join(series_dir, make_filename_valid(info.name))  # 下载目录，以视频名命名

        # 如果目录已经存在，生成不同的目录名，避免视频名相同导致被覆盖
        info.video_dir = make_diff_dir_name(info.video_dir)

        if not os.path.exists(series_dir):
            os.mkdir(series_dir)
        if not os.path.exists(info.video_dir):
            os.mkdir(info.video_dir)

    def _make_metadata_file(self, video_info: T_VideoInfo):
        result = 0
        poster_path = ""
        fanart_path = ""

        if video_info.cover_url:
            poster_path = video_info.video_dir + '/' + 'poster.jpg'  # 封面图保存路径
            # 下载封面
            result = downloader.download_file(poster_path, video_info.cover_url)
        if video_info.thumbnail_url:
            fanart_path = video_info.video_dir + '/' + 'fanart.jpg'  # 背景图保存路径
            # 下载缩略图
            result = result | downloader.download_file(fanart_path, video_info.thumbnail_url)

        if result == 0:
            video_info.metadata.describe = video_info.metadata.describe + '\r\n%s' % video_info.view_url
            video_info.metadata.back_ground_path = fanart_path

            # 生成metadata文件
            make_video_metadata_file(video_info.video_dir, video_info.name, video_info.metadata)

    def _make_source_info_file(self, info: T_VideoInfo):
        make_source_info_file(info.video_dir, info)

    def _download_process(self, video_info: T_VideoInfo, progress: TaskDLProgress = None):
        """此处实现了基本的资源下载逻辑，子类可以根据需要选择继承或重写"""
        video_path = video_info.video_dir + '/' + make_filename_valid('%s.mp4' % video_info.name)  # 视频保存路径

        if '.m3u8' in video_info.download_url.split('/')[-1]:
            downloader.download_mp4_by_m3u8(video_path, video_info.download_url, progress)
        else:
            downloader.download_mp4(video_path, video_info.download_url, progress)

    def _download_process_with_semaphore(self, video_info: T_VideoInfo, progress: TaskDLProgress = None):
        try:
            self._download_process(video_info, progress)
        except Exception:
            raise
        finally:
            self.task_semaphore.release()

    def _start_download_task(self, video_info: T_VideoInfo):
        download_manager.create_task(video_info.name, self._download_process_with_semaphore, video_info)

    @abstractmethod
    def _fetch_info(self, url, **kwargs) -> T_VideoInfo:
        """抓取资源信息，子类需要实现该功能"""
        pass

    def download(self, url, **kwargs):
        default_params = {
            "no_download": False,
        }
        params = {**default_params, **kwargs}
        self.task_semaphore.acquire()

        # 获取视频信息
        video_info = self._fetch_info(url)
        video_info.print_info()

        if params["no_download"]:
            self.task_semaphore.release()
            return

        # 创建目录
        self._make_save_dir(video_info)

        # 创建下载任务
        self._start_download_task(video_info)

        # 创建视频元数据文件
        self._make_metadata_file(video_info)

        # 创建source.txt文件保存下载地址
        self._make_source_info_file(video_info)


class ComicFetcher(SSGBaseFetcher[T_ComicInfo], Generic[T_ComicInfo, T_ChapterInfo]):
    """漫画抓取器基类，已实现漫画下载标准流程，子类需要实现get_info函数获取必须的漫画信息"""

    def __init__(self, max_tasks=1):
        # 由于漫画下载通常要下载大量图片，max_tasks默认设为1，避免请求过多被拒
        super().__init__(max_tasks=max_tasks)
        self.capter_lock = threading.Lock()

    def _make_save_dir(self, info: T_Info):
        # 漫画下载目录说明
        # data  # 下载目录
        # └── site  # 站点目录
        #     └── comic  # 漫画目录
        #         ├── comic_001.cbz  # 第一话
        #         ├── comic_002.cbz  # 第二话
        #         ...
        #
        #         ├── comic_xxx.cbz  # 第xxx话
        #         └── source.txt  # 下载来源信息
        if not self.__class__.site_dir:
            raise ValueError("未指定下载目录!")
        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)

        info.comic_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.title))

        # 如果目录已经存在，生成不同的目录名，避免视频名相同导致被覆盖
        info.comic_dir = make_diff_dir_name(info.comic_dir)
        if not os.path.exists(info.comic_dir):
            os.mkdir(info.comic_dir)

    def _download_process(self, comic_title: str, chapter: T_ChapterInfo, progress: TaskDLProgress = None):
        """此处实现了基本的资源下载逻辑，子类可以根据需要选择继承或重写"""
        comic_info = chapter.comic_info
        comic_dir = comic_info.comic_dir

        image_temp_dir_path = f"{comic_dir}/img-{chapter.id}"  # 漫画图片的临时保存目录

        if not os.path.exists(image_temp_dir_path):
            os.mkdir(image_temp_dir_path)

        res = downloader.download_comic_capter_images(image_temp_dir_path, chapter.image_urls, progress)

        # 图片下载完成，打包成漫画文件
        make_comic(comic_dir, comic_title, image_temp_dir_path, chapter.metadata)

        if progress:
            progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)

        # 删除图片文件夹
        if not config["download"]["comic"]["leave_images"]:
            shutil.rmtree(image_temp_dir_path)
            logger.info('已删除图片缓存')

        return res

    def _download_process_with_semaphore(self, comic_title: str, chapter: T_ChapterInfo, progress: TaskDLProgress = None):
        try:
            # 控制同时只能下载一个章节，避免请求过多
            with self.capter_lock:
                self._download_process(comic_title, chapter, progress)
        except Exception:
            raise
        finally:
            self.task_semaphore.release()

    def _start_download_task(self, chapter: T_ChapterInfo):
        comic_info = chapter.comic_info
        comic_title = make_filename_valid(comic_info.title + "_%03d" % chapter.id)

        # 处理windows路径长度限制问题
        if sys.platform.startswith("win"):
            valid_len = 259 - (len(os.path.abspath(comic_info.comic_dir)) + 1)
            format_max = max(config["download"]["comic"]["format"], key=len, default="")
            if valid_len < len(f'{comic_title}.{format_max}'):
                if valid_len > len(f'{str(chapter.id)}.{format_max}'):
                    # 漫画文件名改为id
                    comic_title = str(chapter.id)
                else:
                    raise ValueError("当前目标路径过长，无法创建漫画文件")

        # 创建下载任务
        logger.info("正在下载第%d章" % chapter.id)
        task_name = comic_title
        download_manager.create_task(task_name, self._download_process_with_semaphore, comic_title, chapter)

    def _make_source_info_file(self, info: T_ComicInfo):
        make_source_info_file(info.comic_dir, info)

    @abstractmethod
    def _fetch_info(self, url, **kwargs) -> T_ComicInfo:
        """抓取资源信息，子类需要实现该功能"""
        pass

    def download(self, url, **kwargs):
        default_params = {
            "no_download": False,
            "chapter_id_list": None
        }
        params = {**default_params, **kwargs}
        self.task_semaphore.acquire()

        # 请求漫画详细信息
        comic_info = self._fetch_info(url, chapter_id_list=params["chapter_id_list"])
        comic_info.print_info()

        if params["no_download"]:
            self.task_semaphore.release()
            return

        # 创建下载目录
        self._make_save_dir(comic_info)

        # 遍历全部漫画章节
        for chapter in comic_info.chapter_list:
            # 创建下载任务
            self._start_download_task(chapter)

            # 创建source.txt文件保存下载地址
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
                # 导入站点包
                full_module_name = f"{package_name}.{module_name}"
                site_module = importlib.import_module(full_module_name)
            except ImportError as e:
                print(f"注册站点异常 {module_name}: {str(e)}")
