import os
from abc import ABC, abstractmethod
from typing import Dict, Type, Optional

from core.metadata.comic import ComicInfo, ChapterInfo
from core.metadata.video import VideoInfo, VideoInfoCache
from core.utils.file_process import make_video_metadata_file, make_source_info_file
from core.utils.file_utils import make_filename_valid, make_diff_dir_name
from core.utils.trace import *
from core.request import seserequest as ssreq


class AbstractFetcher(ABC):
    """站点抓取器基类"""

    @abstractmethod
    def get_info(self, url, **kwargs):
        """
        获取资源信息
        Args:
            **kwargs:
            url: 请求资源地址

        Returns: 返回一个包含资源信息的对象

        """
        pass

    @abstractmethod
    def download(self, url, **kwargs):
        """
        下载资源
        Args:
            url: 请求资源地址
            **kwargs: 可选配置参数

        """
        pass


class VideoFetcher(AbstractFetcher):
    """视频抓取器基类，已实现视频下载标准流程，子类需要实现get_info函数获取必须的视频信息"""
    site_dir = ""  # 站点目录，需要在子类中指定目录

    def __init__(self):
        self.video_info_cache = VideoInfoCache(10)

    def _make_save_dir(self, video_info: VideoInfo):
        # 视频下载目录说明
        # data  # 下载目录
        # └── site  # 站点目录
        #     └── artist  # 作者目录
        #         └── video  # 视频目录
        #             ├── video.mp4  # 视频文件
        #             ├── video.nfo  # 元数据文件
        #             ├── fanart.jpg  # 背景图片
        #             ├── poster.jpg  # 封面图片
        #             └── source.txt  # 下载来源信息
        if not self.site_dir:
            raise ValueError("未指定下载目录!")

        artist_dir = self.__class__.site_dir + '%s' % make_filename_valid(video_info.metadata.artist)  # 中间目录，主要用来分类同一个作者的作品
        video_info.video_dir = '%s/%s' % (artist_dir, make_filename_valid(video_info.name))  # 下载目录，以视频名命名

        # 如果目录已经存在，生成不同的目录名，避免视频名相同导致被覆盖
        video_info.video_dir = make_diff_dir_name(video_info.video_dir)

        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)
        if not os.path.exists(artist_dir):
            os.mkdir(artist_dir)
        if not os.path.exists(video_info.video_dir):
            os.mkdir(video_info.video_dir)

    def _make_metadata_file(self, video_info: VideoInfo):
        poster_path = video_info.video_dir + '/' + 'poster.jpg'  # 封面图保存路径
        fanart_path = video_info.video_dir + '/' + 'fanart.jpg'  # 背景图保存路径

        if ssreq.download_file(poster_path, video_info.cover_url) | \
                ssreq.download_file(fanart_path, video_info.thumbnail_url) == 0:

            video_info.metadata.describe = video_info.metadata.describe + '\r\n%s' % video_info.view_url
            video_info.metadata.back_ground_path = fanart_path

            # 生成metadata文件
            make_video_metadata_file(video_info.video_dir, video_info.name, video_info.metadata)

    def _make_source_info_file(self, video_info: VideoInfo):
        make_source_info_file(video_info.video_dir, video_info)

    def _start_download(self, video_info: VideoInfo):
        video_path = video_info.video_dir + '/' + make_filename_valid('%s.mp4' % video_info.name)  # 视频保存路径

        if '.m3u8' in video_info.download_url.split('/')[-1]:
            ssreq.download_task(video_info.name, ssreq.download_mp4_by_m3u8, video_path, video_info.download_url)
        else:
            ssreq.download_task(video_info.name, ssreq.download_mp4, video_path, video_info.download_url)

    @abstractmethod
    def get_info(self, url, **kwargs) -> VideoInfo:
        pass

    def download(self, url, **kwargs):
        # 获取视频信息
        video_info = self.get_info(url)
        video_info.print_info()

        # 创建目录
        self._make_save_dir(video_info)

        # 创建下载任务
        self._start_download(video_info)

        # 创建视频元数据文件
        self._make_metadata_file(video_info)

        # 创建source.txt文件保存下载地址
        self._make_source_info_file(video_info)


class ComicFetcher(AbstractFetcher):
    """漫画抓取器基类，已实现漫画下载标准流程，子类需要实现get_info函数获取必须的漫画信息"""
    site_dir = ""  # 站点目录，需要在子类中指定目录

    def _make_save_path(self, comic_info: ComicInfo):
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
        if not self.site_dir:
            raise ValueError("未指定下载目录!")

        comic_info.comic_dir = self.site_dir + "/" + make_filename_valid(comic_info.title)

        # 如果目录已经存在，生成不同的目录名，避免视频名相同导致被覆盖
        comic_info.comic_dir = make_diff_dir_name(comic_info.comic_dir)
        if not os.path.exists(comic_info.comic_dir):
            os.mkdir(comic_info.comic_dir)

    def _start_download(self, chapter: ChapterInfo):
        comic_info = chapter.comic_info

        # 创建下载任务
        SESE_PRINT("正在下载第%d章" % chapter.id)
        comic_title = make_filename_valid(comic_info.title + "_%03d" % chapter.id)
        task_name = comic_title
        ssreq.download_task(task_name, ssreq.download_comic_capter,
                            comic_info.comic_dir, comic_title, chapter.image_urls, chapter)

    def _make_source_info_file(self, comic_info: ComicInfo):
        make_source_info_file(comic_info.comic_dir, comic_info)

    @abstractmethod
    def get_info(self, url, **kwargs) -> ComicInfo:
        pass

    def download(self, url, **kwargs):
        chapter_id_list = kwargs.get("chapter_id_list", None)

        # 请求漫画详细信息
        comic_info = self.get_info(url, chapter_id_list=chapter_id_list)
        comic_info.print_info()

        # 创建下载目录
        self._make_save_path(comic_info)

        # 遍历全部漫画章节
        for chapter in comic_info.chapter_list:
            # 创建下载任务
            self._start_download(chapter)

            # 创建source.txt文件保存下载地址
            self._make_source_info_file(comic_info)


class FetcherRegistry:
    """Fetcher类注册器"""
    _registry: Dict[str, Type[AbstractFetcher]] = {}

    @classmethod
    def register(cls, site_name: str):
        """注册装饰器"""

        def decorator(fetcher_class: Type[AbstractFetcher]):
            if not issubclass(fetcher_class, AbstractFetcher):
                raise TypeError(f"{fetcher_class} 必须继承自 AbstractFetcher")
            cls._registry[site_name] = fetcher_class
            SESE_TRACE(LOG_INFO, f"注册Fetcher类{fetcher_class}")
            return fetcher_class

        return decorator

    @classmethod
    def get_fetcher(cls, site_name: str, *args, **kwargs) -> Optional[AbstractFetcher]:
        """获取指定站点的下载器实例"""
        fetcher_class = cls._registry.get(site_name)
        if not fetcher_class:
            raise ValueError(f"未注册的站点: {site_name}")
        return fetcher_class(*args, **kwargs)

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
