import asyncio
import os
from typing import Generic

from ...output.video import make_video_metadata_file
from ...utils.file_utils import make_diff_dir_name, make_filename_valid
from ...utils.trace import logger
from .. import downloader, task_downloader
from ..downloadtask import DownloadTask, FileDLProgress, download_manager
from .base import SSGBaseFetcher, T_VideoInfo
from .info import VideoInfoCache, make_source_info_file


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
