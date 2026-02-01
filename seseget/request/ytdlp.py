import yt_dlp
from .downloadtask import TaskDLProgress, FileDLProgress
from ..utils.trace import SSGLogger, logger


yt_logger = SSGLogger("yt_dlp")


class YtDlpLogger:
    def debug(self, msg):
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            yt_logger.debug(msg)
        else:
            yt_logger.info(msg)

    def info(self, msg):
        yt_logger.info(msg)

    def warning(self, msg):
        yt_logger.warning(msg)

    def error(self, msg):
        yt_logger.error(msg)


DEFAULT_FORMAT = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
VIDEO_FORMAT = 'bestvideo[ext=mp4]/bestvideo'
AUDIO_FORMAT = 'bestaudio[ext=m4a]/bestaudio'


def get_info(url, extend_opts=None):
    ydl_opts = {
        'logger': YtDlpLogger(),
        'source_address': '0.0.0.0',
        'verbose': True,
        'retries': 3,
    }
    if extend_opts is not None:
        ydl_opts.update(extend_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as result:
        logger.error('Error! info: %s' % result)
        return None

    return info


def download_by_yt_dlp(filename, url, extend_opts=None, progress: TaskDLProgress = None):
    """通过yt_dlp下载视频"""
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
        #     logger.debug(f"\r\n{d}")
        #     with open(f"{d['filename'].split('.')[-1]}.py", "wb") as f:
        #         f.write(f"{d}".encode())

        # logger.info(f"current_progress:{downloaded}/{total}")
        progress.add_progress(file_name, total=total)
        progress.set_downloaded(file_name, downloaded)
        progress.set_status(status)

    # 下载配置
    ydl_opts = {
        'logger': YtDlpLogger(),
        'format': 'bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b',
        #'outtmpl': dir + '/%(title)s.%(ext)s',
        'outtmpl': filename,
        'source_address': '0.0.0.0',
        'verbose': True,
        'retries': 3,
        'progress_hooks': [progress_hook],
        'noprogress': True,
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }
    if extend_opts is not None:
        ydl_opts.update(extend_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            progress.init_progress()
            progress.set_progress_count(2)
            progress.set_status(FileDLProgress.Status.DOWNLOADING)
            error_code = ydl.download([url])

            if error_code:
                logger.error(f'YoutubeDL.download error! code:{error_code}')
                progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
                return -1
            else:
                progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)

    except Exception as result:
        logger.error('Error! info: %s' % result)
        progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        return -1

    return 0
