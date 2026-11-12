import asyncio
import os
import re
import shutil
import tempfile

from ..utils.file_utils import get_file_basename
from ..utils.subprocess_utils import exec_cmd
from ..utils.trace import logger
from . import ytdlp
from .downloader import DownloadObserver, _download_file, _download_files
from .downloadtask import DownloadTask, FileDLProgress, TaskDLProgress
from .requests import async_request


class TaskProgressObserver:
    """把底层下载事件转换为 TaskDLProgress 更新。"""

    def __init__(self, progress: TaskDLProgress):
        self.progress = progress

    def on_start(self, file_name: str, total: int) -> None:
        self.progress.add_progress(file_name, total=total)

    def on_chunk(self, file_name: str, size: int) -> None:
        self.progress.update(file_name, size)

    def on_skip(self, file_name: str, total: int) -> None:
        self.progress.add_progress(file_name, total=total)
        self.progress.update(file_name, total)

    def on_progress(self, file_name: str, downloaded: int, total: int) -> None:
        self.progress.add_progress(file_name, total=total)
        self.progress.set_downloaded(file_name, downloaded)

    def on_status(self, status: str) -> None:
        self.progress.set_status(status)


def _observer(task: DownloadTask) -> DownloadObserver:
    return TaskProgressObserver(task.task_progress)


async def download_mp4(task: DownloadTask, filename, url):
    """下载 mp4 视频。"""
    progress = task.task_progress
    progress.init_progress()
    progress.set_progress_count(1)
    progress.set_status(FileDLProgress.Status.DOWNLOADING)

    result = await _download_file(filename, url, observer=_observer(task))

    status = (
        FileDLProgress.Status.DOWNLOAD_OK
        if result == 0
        else FileDLProgress.Status.DOWNLOAD_ERROR
    )
    progress.set_status(status)
    if result == 0:
        logger.info(f"{get_file_basename(filename)} Download OK!")
    else:
        logger.info(f"{get_file_basename(filename)} Download ERROR!")
    return result


async def download_mp4_by_merge_video_audio(task: DownloadTask, filename, video_url, audio_url, headers):
    """下载视频和音频文件并合并成 mp4 文件。"""
    progress = task.task_progress
    dir = os.path.dirname(filename)
    cache_dir = os.path.join(dir, "cache")
    audio_path = os.path.join(cache_dir, "cache.mp3")
    video_path = os.path.join(cache_dir, "cache.mp4")
    os.makedirs(cache_dir, exist_ok=True)

    progress.init_progress()
    progress.set_progress_count(2)
    progress.set_status(FileDLProgress.Status.DOWNLOADING)
    if await _download_files(
            [audio_path, video_path],
            [audio_url, video_url],
            observer=_observer(task),
            headers=headers) != 0:
        logger.error("download_files failed!")
        progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        return -1

    logger.info("开始合并音视频文件...")
    progress.set_status(FileDLProgress.Status.PROCESS)

    # ffmpeg 是 CPU 密集型子进程，放入线程池执行
    merged = await asyncio.to_thread(
        exec_cmd,
        ["ffmpeg", "-hide_banner", "-i", f"{video_path}", "-i", f"{audio_path}", "-c:v", "copy", "-c:a", "aac",
         "-strict", "experimental", f"{filename}"]
    )

    if not merged or not os.path.exists(filename) or os.path.getsize(filename) == 0:
        logger.error("ffmpeg 合并失败，保留缓存以便重试: %s", cache_dir)
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except OSError as exc:
                logger.warning("删除不完整输出失败: %s", exc)
        progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        return -1

    logger.info(f"合并完成，保存在{filename}")
    progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)

    shutil.rmtree(cache_dir)
    logger.info("已删除缓存文件")

    return 0


async def _get_ts_list_from_m3u8(url):
    ts_list: list[str] = []

    # 异步下载 m3u8 文件
    response = await async_request("GET", url, stream=True)

    # m3u8 文件中的 uri
    uri_list = re.findall(r'(?<=\n)\w.*', response.text)
    for uri in uri_list:
        if '.m3u8' in uri:
            m3u8_url = url.rsplit('/', 1)[0] + '/' + uri
            ts_list = ts_list + await _get_ts_list_from_m3u8(m3u8_url)
        elif '.ts' in uri:
            ts_url = url.rsplit('/', 1)[0] + '/' + uri
            ts_list.append(ts_url)

    return ts_list


async def download_mp4_by_m3u8(task: DownloadTask, filename, url):
    """下载 m3u8 文件，保存为 mp4 格式。"""
    progress = task.task_progress
    ts_list = await _get_ts_list_from_m3u8(url)

    if not ts_list:
        progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        raise ValueError(f"m3u8 中没有找到 ts 分片: {url}")

    progress.init_progress()
    progress.set_progress_count(len(ts_list))
    progress.set_status(FileDLProgress.Status.DOWNLOADING)

    semaphore = asyncio.Semaphore(10)

    # 每个 m3u8 任务使用独立临时目录，避免并发任务互相污染
    with tempfile.TemporaryDirectory(prefix="seseget-m3u8-") as temp_dir:
        async def _download_ts(ts_url, idx):
            ts_name = '%08d.ts' % idx
            async with semaphore:
                await _download_file(
                    os.path.join(temp_dir, ts_name), ts_url, True, None
                )
            return ts_name

        tasks = [
            _download_ts(ts_url, idx)
            for idx, ts_url in enumerate(ts_list, start=1)
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"下载失败！info: {e}")
            progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
            raise

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"下载失败！info: {result}")
                progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
                raise result

        # 按分片顺序写 concat 列表，不能依赖并发下载的完成顺序
        ts_names = list(results)
        concat_list_path = os.path.join(temp_dir, "ts_files_list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for ts_name in ts_names:
                f.write(f"file '{ts_name}'\n")

        logger.info('下载完成!')
        progress.set_status(FileDLProgress.Status.PROCESS)

        # ffmpeg 拼接 ts 文件，保存为 mp4
        ok = await asyncio.to_thread(
            exec_cmd,
            [
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", concat_list_path, "-c", "copy", filename,
            ]
        )
        if not ok:
            progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
            raise RuntimeError(f"ffmpeg 拼接 m3u8 失败: {url}")

        progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)
        return 0


async def download_comic_capter_images(task: DownloadTask, save_dir: str, image_urls):
    """下载漫画章节图片。"""
    progress = task.task_progress
    progress.init_progress()
    progress.set_progress_count(len(image_urls))
    progress.set_status(FileDLProgress.Status.DOWNLOADING)

    logger.debug(f"image_urls: {image_urls}")

    semaphore = asyncio.Semaphore(10)

    async def _download_image(index, url):
        image_name = "%05d.jpg" % index
        image_path = save_dir + "/" + image_name
        async with semaphore:
            await _download_file(image_path, url, True, _observer(task))

    tasks = [_download_image(idx, url) for idx, url in enumerate(image_urls)]

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"下载失败！info: {r}")
                progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
                raise r
    except Exception as e:
        logger.error(f"下载失败！info: {e}")
        progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        raise

    logger.info("下载完成！")
    progress.set_status(FileDLProgress.Status.PROCESS)


def download_ytdlp(task: DownloadTask, filename, url, extend_opts=None):
    """通过 yt-dlp 下载视频；同步函数，调用方负责放入线程池。"""
    progress = task.task_progress
    progress.init_progress()
    progress.set_progress_count(2)
    progress.set_status(FileDLProgress.Status.DOWNLOADING)

    result = ytdlp.download_by_yt_dlp(
        filename,
        url,
        extend_opts,
        _observer(task),
    )

    status = (
        FileDLProgress.Status.DOWNLOAD_OK
        if result == 0
        else FileDLProgress.Status.DOWNLOAD_ERROR
    )
    progress.set_status(status)

    return result
