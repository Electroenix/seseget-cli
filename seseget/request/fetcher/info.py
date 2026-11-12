import asyncio
from collections import OrderedDict

from ...config.config_manager import config
from ...metadata.comic import ComicMetaData
from ...metadata.video import VideoMetaData
from ...utils.trace import logger


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
