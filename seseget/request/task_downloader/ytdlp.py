from .. import ytdlp_engine
from ..downloadtask import DownloadTask, FileDLProgress
from .progress import observer_for


def download_ytdlp(task: DownloadTask, filename, url, extend_opts=None):
    """通过 yt-dlp 下载视频；同步函数，调用方负责放入线程池。"""
    progress = task.task_progress
    progress.init_progress()
    progress.set_progress_count(2)
    progress.set_status(FileDLProgress.Status.DOWNLOADING)

    result = ytdlp_engine.download_by_yt_dlp(
        filename,
        url,
        extend_opts,
        observer_for(task),
    )

    status = (
        FileDLProgress.Status.DOWNLOAD_OK
        if result == 0
        else FileDLProgress.Status.DOWNLOAD_ERROR
    )
    progress.set_status(status)

    return result
