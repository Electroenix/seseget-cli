import asyncio
import os
import shutil
import sys
from abc import abstractmethod
from typing import Generic

from ...config.config_manager import config
from ...output.comic import comic_missing_formats, package_comic
from ...utils.file_utils import make_filename_valid
from ...utils.trace import logger
from .. import task_downloader
from ..downloadtask import DownloadTask, FileDLProgress, download_manager
from .base import SSGBaseFetcher, T_ChapterInfo, T_ComicInfo
from .info import ComicInfo, make_source_info_file


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
