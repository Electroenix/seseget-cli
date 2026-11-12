"""任务级下载实现。

``media`` 只依赖普通下载器和 HTTP 会话；``ytdlp`` 才加载 yt-dlp。
"""

from .media import (
    download_comic_capter_images,
    download_mp4,
    download_mp4_by_m3u8,
    download_mp4_by_merge_video_audio,
)
from .progress import TaskProgressObserver

__all__ = [
    "TaskProgressObserver",
    "download_comic_capter_images",
    "download_mp4",
    "download_mp4_by_m3u8",
    "download_mp4_by_merge_video_audio",
]
