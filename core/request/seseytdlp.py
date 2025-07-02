import os
import yt_dlp
from core.request.downloadtask import ProgressCallback, TaskDLProgress
from core.utils.trace import *


class YtDlpLogger:
    def debug(self, msg):
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            SESE_TRACE(LOG_DEBUG, msg)
        else:
            if msg.startwith("[download] "):
                print(msg)
            else:
                SESE_TRACE(LOG_INFO, msg)

    def info(self, msg):
        if msg.startwith("[download] "):
            print(msg)
        else:
            SESE_TRACE(LOG_INFO, msg)

    def warning(self, msg):
        SESE_TRACE(LOG_WARNING, msg)

    def error(self, msg):
        SESE_TRACE(LOG_ERROR, msg)


DEFAULT_FORMAT = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
VIDEO_FORMAT = 'bestvideo[ext=mp4]/bestvideo'
AUDIO_FORMAT = 'bestaudio[ext=m4a]/bestaudio'


class YDLClient:
    """封装yt_dlp操作，适配项目功能"""

    def __init__(self):
        self.progress = TaskDLProgress()

    def get_info(self, url):
        ydl_opts = {
            'source_address': '0.0.0.0',
            'verbose': True,
            'retries': 3,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as result:
            SESE_TRACE(LOG_ERROR, 'Error! info: %s' % result)
            return -1

        return info

    def _progress_hook(self, d: dict):
        file_name = ""
        status = ""
        downloaded = 0
        total = 0

        if "file_name" in d:
            file_name = d["file_name"]
        if "status" in d:
            status = d["status"]
        if "downloaded_bytes" in d:
            downloaded = d["downloaded_bytes"]
        if "total_bytes" in d:
            total = d["total_bytes"]

        self.progress.update(file_name, downloaded=downloaded, total=total, status=status)

    def _download(self, filename, url, progress_callback: ProgressCallback = None, format_opt: str = DEFAULT_FORMAT):
        """通过yt_dlp下载视频/音频"""
        dir = os.path.dirname(filename)
        if not os.path.exists(dir):
            os.mkdir(dir)

        # 下载配置
        ydl_opts = {
            # 'logger': YtDlpLogger(),
            'format': format_opt,
            'outtmpl': dir + '/%(title)s.%(ext)s',
            'source_address': '0.0.0.0',
            'verbose': True,
            'retries': 3,
            'progress_hooks': [self._progress_hook],
            'merge_output_format': 'mp4',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download([url])

                if error_code:
                    SESE_TRACE(LOG_ERROR, f'YoutubeDL.download error! code:{error_code}')
                    progress_callback(status="error")
                    return -1
                else:
                    progress_callback(status="OK")

        except Exception as result:
            SESE_TRACE(LOG_ERROR, 'Error! info: %s' % result)
            progress_callback(status="error")
            return -1

        return 0

    def download(self, filename, url, progress_callback: ProgressCallback = None):
        """下载合并后的完整视频"""
        return self._download(filename, url, progress_callback, DEFAULT_FORMAT)

    def download_video(self, filename, url, progress_callback: ProgressCallback = None):
        """下载单独视频"""
        return self._download(filename, url, progress_callback, VIDEO_FORMAT)

    def download_audio(self, filename, url, progress_callback: ProgressCallback = None):
        """下载单独音频"""
        return self._download(filename, url, progress_callback, AUDIO_FORMAT)


def download_by_yt_dlp(filename, url, progress_callback: ProgressCallback = None):
    """通过yt_dlp下载视频"""
    dir = os.path.dirname(filename)
    if not os.path.exists(dir):
        os.mkdir(dir)

    # 下载进度回调
    def progress_hook(d):
        file_name = ""
        status = ""
        downloaded = 0
        total = 0

        if "filename" in d:
            file_name = d["filename"]
        if "status" in d:
            status = d["status"]
        if "downloaded_bytes" in d:
            downloaded = d["downloaded_bytes"]
        if "total_bytes" in d:
            total = d["total_bytes"]

        # if d["status"] == "finished":
        #     SESE_TRACE(LOG_DEBUG, f"\r\n{d}")
        #     with open(f"{d['filename'].split('.')[-1]}.py", "wb") as f:
        #         f.write(f"{d}".encode())

        progress_callback(file_name, downloaded=downloaded, total=total, status=status)

    # 下载配置
    ydl_opts = {
        # 'logger': YtDlpLogger(),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': dir + '/%(title)s.%(ext)s',
        'source_address': '0.0.0.0',
        'verbose': True,
        'retries': 3,
        'progress_hooks': [progress_hook],
        'merge_output_format': 'mp4',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            progress_callback(status="downloading")
            error_code = ydl.download([url])

            if error_code:
                SESE_TRACE(LOG_ERROR, f'YoutubeDL.download error! code:{error_code}')
                progress_callback(status="ERROR")
                return -1
            else:
                progress_callback(status="OK")

    except Exception as result:
        SESE_TRACE(LOG_ERROR, 'Error! info: %s' % result)
        progress_callback(status="ERROR")
        return -1

    return 0
