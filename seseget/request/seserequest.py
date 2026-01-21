import os
import time
import re
import shutil
import threading
import copy
import traceback

from curl_cffi import requests
from urllib.parse import urlparse
from urllib.request import getproxies
from typing import Dict

from ..metadata.comic import ChapterInfo
from ..utils.thread_utils import SeseThreadPool
from ..utils.trace import *
from .downloadtask import download_manager, TaskDLProgress, ProgressStatus
from ..utils.file_process import make_comic
from ..config.config_manager import config
from ..utils.file_utils import get_file_basename
from ..utils.subprocess_utils import exec_cmd


class SessionManager:
    """智能 Session 管理器，按请求主机自动分配独立 Session"""

    def __init__(self):
        # 存储不同主机的 Session 对象 {host: Session}
        self._sessions: Dict[str, requests.Session] = {}
        self._lock = threading.Lock()

    def _get_session_for_host(self, host: str) -> requests.Session:
        """获取或创建指定主机的 Session"""
        with self._lock:
            if host not in self._sessions:
                # 创建新 Session 并应用配置
                session = requests.Session()

                self._sessions[host] = session
            # SESE_PRINT(f"当前session列表：{list(self._sessions.keys())}")
            return self._sessions[host]

    def request(self, method: requests.HttpMethod, url: str, **kwargs) -> requests.Response:
        """发起请求，自动路由到对应主机的 Session"""
        if "headers" not in kwargs:
            kwargs["headers"] = copy.copy(ss_headers)
        SESE_TRACE(LOG_DEBUG, f'headers: {kwargs["headers"]}')
        if "proxies" not in kwargs:
            proxy_config = config["common"]["proxy"]
            if proxy_config:
                proxies = {
                    "http": proxy_config,
                    "https": proxy_config,
                }
                kwargs["proxies"] = proxies
            else:
                sys_proxies = getproxies()
                proxies = {
                    "http": sys_proxies.get("http"),
                    "https": sys_proxies.get("https"),
                }
                kwargs["proxies"] = proxies
            SESE_TRACE(LOG_DEBUG, f'proxy: {kwargs["proxies"]}')
        if "impersonate" not in kwargs:
            kwargs["impersonate"] = "chrome110"
        if "timeout" not in kwargs:
            kwargs["timeout"] = settings.REQUEST_TIMEOUT

        parsed_url = urlparse(url)
        host = parsed_url.netloc  # 提取主机名（如 'api.example.com'）
        session = self._get_session_for_host(host)

        return session.request(method, url, **kwargs)

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def close_all(self):
        """关闭所有 Session 释放资源"""
        with self._lock:
            for host, session in self._sessions.items():
                session.close()
                SESE_TRACE(LOG_DEBUG, f"释放Session: {host}")
            self._sessions.clear()


ss_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}
# request_session = requests.Session()
ss_session = SessionManager()


def request(method, url, **kwargs):
    """
    发送请求
    Args:
        method: 请求方法
        url: 请求地址
        **kwargs: 附加参数，将传递给实际发送请求的函数

    Returns: 响应对象

    """
    retry_max = 3
    retry_times = 0
    response = None

    while True:
        try:
            response = ss_session.request(method, url, **kwargs)
            SESE_DEBUG(f'request headers: {response.request.headers}')
            break
        except Exception as result:
            if retry_times < retry_max:
                SESE_TRACE(LOG_ERROR, 'Error! info: %s' % result)
                SESE_PRINT("GET %s Failed, Retry(%d)..." % (url, retry_times))
                retry_times = retry_times + 1
                time.sleep(1)
                continue
            else:
                SESE_TRACE(LOG_ERROR, 'Error! retry max - %d!' % retry_max)
                break

    return response


def _download_file(file_name, url, auto_retry=True, progress: TaskDLProgress = None, **kwargs):
    """
    下载单个文件
    Args:
        file_name: 文件名，完整路径
        url: 下载地址
        auto_retry: 下载异常时是否自动重试
        progress: 控制下载进度的对象
        **kwargs: 附加参数，将传递给实际发送请求的函数

    """
    retry_max = 3
    retry_times = 0

    while True:
        try:
            f_size = 0
            if os.path.exists(file_name):
                f_size = os.path.getsize(file_name)

            if f_size > 0:
                # 如果本地已存在文件，设置从断点开始继续下载
                if "headers" not in kwargs:
                    kwargs["headers"] = copy.copy(ss_headers)
                kwargs["headers"]['Range'] = 'bytes=%d-' % f_size
            elif "headers" in kwargs and "Range" in kwargs["headers"]:
                # 文件不存在但是设置了Range，则去除Range字段
                kwargs["headers"].pop("Range")

            SESE_TRACE(LOG_DEBUG, f"request [{url}]")

            response = ss_session.request("GET", url=url, stream=True, **kwargs)
            if response:
                SESE_TRACE(LOG_DEBUG, f"[response open]")

            total_size = 0
            read_size = 0
            file_mode = ''

            try:
                if response.status_code == 200:
                    # 非续传模式或服务器不支持续传
                    file_mode = 'wb'  # 覆盖模式
                    SESE_TRACE(LOG_DEBUG, f"respone[200], Content-Length: {response.headers['Content-Length']}")
                    total_size = int(response.headers['Content-Length'])

                elif response.status_code == 206:
                    # 续传模式
                    file_mode = 'ab'  # 追加模式
                    SESE_TRACE(LOG_DEBUG, f"respone[206], Content-Length: {response.headers['Content-Length']}")
                    total_size = f_size + int(response.headers['Content-Length'])

                elif response.status_code == 416:
                    # 文件超出Range范围
                    remote_file_size = int(response.headers['Content-Range'].split("/")[-1])
                    if f_size == remote_file_size:
                        # 文件已经完整，直接return
                        SESE_TRACE(LOG_DEBUG, "检测到文件(%s)已存在" % file_name)
                        if progress is not None:
                            progress.add_progress(file_name, total=f_size)
                            progress.update(file_name, f_size)
                        response.close()
                        SESE_TRACE(LOG_DEBUG, f"[response close]")
                        return 0
                    # 文件大小错误，删除文件并重试下载
                    SESE_TRACE(LOG_ERROR,
                               f"文件大小错误，删除文件重新下载，file: {file_name}, (f_size:{f_size}, remote_file_size:{remote_file_size})")
                    os.remove(file_name)
                    response.close()
                    SESE_TRACE(LOG_DEBUG, f"[response close]")
                    continue

                response.raise_for_status()

                if progress is not None:
                    progress.add_progress(file_name, total=total_size)

                with open(file_name, file_mode) as f:
                    # for data in response.iter_content(chunk_size=1024):
                    for data in response.iter_content():  # curl_cffi not accept chunk_size
                        size = f.write(data)
                        read_size = read_size + size
                        if progress is not None:
                            progress.update(file_name, size)

                    break

            except Exception:
                if response:
                    SESE_TRACE(LOG_DEBUG, f"Error! response header: {response.headers}")
                raise

            finally:
                response.close()
                SESE_TRACE(LOG_DEBUG, f"[response close]")

        except Exception as result:
            if auto_retry:
                if retry_times < retry_max:
                    SESE_TRACE(LOG_DEBUG, 'Error! info: %s' % result)
                    SESE_TRACE(LOG_DEBUG, "GET %s Failed, Retry(%d)..." % (url, retry_times))
                    retry_times = retry_times + 1
                    time.sleep(5)
                    continue
                else:
                    raise
            else:
                SESE_TRACE(LOG_ERROR, 'Error! info: %s' % result)
                retry = input('下载失败，是否重新下载(y/n)')
                if retry == 'y':
                    continue
                else:
                    raise

    return 0


def _handle_exception(future):
    """处理完成任务的异常"""
    if future.exception():
        exc = future.exception()
        SESE_TRACE(LOG_ERROR, "下载任务异常! info: %s\r\n\r\nTraceback:\r\n%s" %
                   (exc, ''.join(traceback.format_tb(exc.__traceback__))))


def _download_files(file_name_list: list[str],
                    url_list: list[str],
                    *,
                    max_workers=10,
                    progress: TaskDLProgress = None,
                    **kwargs):
    """
    下载多个文件
    Args:
        file_name_list: 文件保存路径列表
        url_list: 下载地址列表
        max_workers: 最大同时下载数
        progress: TaskDLProgress对象，管理下载进度
        **kwargs:

    Returns:

    """
    if len(file_name_list) != len(url_list):
        SESE_TRACE(LOG_ERROR, "文件与下载地址数量不匹配！")
        return -1

    with SeseThreadPool(max_workers=max_workers) as pool:
        index = 0
        for file_name in file_name_list:
            url = url_list[index]

            # 创建下载任务
            pool.submit(_download_file, file_name, url, True, progress, **kwargs)
            index = index + 1

        SESE_PRINT("已提交所有下载任务！")

        try:
            pool.wait_all()
            SESE_PRINT("全部文件下载完成！")

        except Exception as e:
            SESE_TRACE(LOG_ERROR, f"下载失败！info: {e}")
            raise

    return 0


def download_file(file_name, url, **kwargs):
    """下载单个文件"""
    result = _download_file(file_name, url, **kwargs)
    return result


def download_file_ex(file_name: str,
                     url: str,
                     *,
                     max_workers=10,
                     progress: TaskDLProgress = None,
                     **kwargs):
    """下载单个文件"""
    result = _download_file(file_name, url, **kwargs)
    return result


def download_files(file_name_list: list[str], url_list: list[str]):
    """下载多个文件"""
    result = _download_files(file_name_list, url_list)
    return result


def download_files_ex(file_name_list: list[str],
                      url_list: list[str],
                      *,
                      max_workers=10,
                      progress: TaskDLProgress = None,
                      **kwargs):
    """下载多个文件"""
    result = _download_files(file_name_list,
                             url_list,
                             max_workers=max_workers,
                             progress=progress,
                             **kwargs)
    return result


def download_mp4(filename, url, progress: TaskDLProgress = None):
    """下载mp4视频"""
    progress.init_progress()
    progress.set_progress_count(1)
    progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)

    result = _download_file(filename, url, progress=progress)

    if result == 0:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)
        SESE_PRINT(f"{get_file_basename(filename)} Download OK!")
    else:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_ERROR)
        SESE_PRINT(f"{get_file_basename(filename)} Download ERROR!")
    return result


def download_mp4_by_merge_video_audio(filename, video_url, audio_url, headers,
                                      progress: TaskDLProgress = None):
    """下载视频和音频文件并合并成mp4文件"""
    dir = os.path.dirname(filename)
    cache_dir = os.path.join(dir, "cache")
    audio_path = os.path.join(cache_dir, "cache.mp3")
    video_path = os.path.join(cache_dir, "cache.mp4")
    if not os.path.exists(dir):
        os.mkdir(dir)
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)

    progress.init_progress()
    progress.set_progress_count(2)
    progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)
    if _download_files(
            [audio_path, video_path],
            [audio_url, video_url],
            progress=progress,
            headers=headers) != 0:
        SESE_TRACE(LOG_ERROR, "download_files failed!")
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_ERROR)
        return -1

    SESE_PRINT("开始合并音视频文件...")
    progress.set_status(ProgressStatus.PROGRESS_STATUS_PROCESS)

    # 开始合并音视频文件
    exec_cmd(["ffmpeg", "-hide_banner", "-i", f"{video_path}", "-i", f"{audio_path}", "-c:v", "copy", "-c:a", "aac",
              "-strict", "experimental", f"{filename}"])

    SESE_PRINT(f"合并完成，保存在{filename}")
    progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)

    shutil.rmtree(cache_dir)
    SESE_PRINT(f"已删除缓存文件")

    return 0


def _get_ts_list_from_m3u8(url):
    ts_list = []
    headers = copy.copy(ss_headers)

    # 下载m3u8文件
    response = ss_session.request("GET", url=url, headers=headers, stream=True)

    # m3u8文件中的uri
    uri_list = re.findall(r'(?<=\n)\w.*', response.text)
    for uri in uri_list:
        if '.m3u8' in uri:
            m3u8_url = url.rsplit('/', 1)[0] + '/' + uri
            ts_list = ts_list + _get_ts_list_from_m3u8(m3u8_url)
        elif '.ts' in uri:
            ts_url = url.rsplit('/', 1)[0] + '/' + uri
            ts_list.append(ts_url)

    return ts_list


def download_mp4_by_m3u8(filename, url, progress: TaskDLProgress = None):
    """下载m3u8文件，保存为mp4格式"""
    # 获取所有ts文件url
    ts_list = _get_ts_list_from_m3u8(url)
    ts_index = 0

    if progress is not None:
        progress.init_progress()
        progress.set_progress_count(len(ts_list))
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)

    with SeseThreadPool(max_workers=10) as pool:
        for ts_url in ts_list:
            ts_index = ts_index + 1
            f_ts_name = '%08d.ts' % ts_index

            if not os.path.exists('ts_temp'):
                os.mkdir('ts_temp')

            # 加入下载线程
            pool.submit(_download_file, 'ts_temp/%s' % f_ts_name, ts_url, True, None)

            with open('ts_temp/ts_files_list.txt', 'a') as f_ts_files_list:
                f_ts_files_list.write('file \'%s\'\r\n' % f_ts_name)

        try:
            pool.wait_all()

        except Exception as e:
            SESE_TRACE(LOG_ERROR, f"下载失败！info: {e}")
            if progress:
                progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_ERROR)
            raise

    SESE_PRINT('下载完成!')
    if progress:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_PROCESS)

    # ffmpeg拼接ts文件，保存为mp4
    exec_cmd(["ffmpeg", "-f", "concat", "-safe", "0", "-i", "ts_temp/ts_files_list.txt", "-c", "copy", filename])
    shutil.rmtree('ts_temp')

    if progress:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)
    return 0


def download_comic_capter(save_dir: str, comic_title: str, image_urls, chapter: ChapterInfo,
                          progress: TaskDLProgress = None):
    """
    下载漫画章节
    Args:
        save_dir: 漫画保存目录
        comic_title: 漫画系列名
        image_urls: 存放漫画图片的url列表
        chapter: 存放章节信息的对象
        progress: 控制下载进度的对象

    """
    image_index = 1
    image_temp_dir_path = save_dir + "/" + comic_title  # 漫画图片的临时保存目录

    if not os.path.exists(image_temp_dir_path):
        os.mkdir(image_temp_dir_path)

    if progress is not None:
        progress.init_progress()
        progress.set_progress_count(len(image_urls))
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)

    SESE_TRACE(LOG_DEBUG, f"image_urls: {image_urls}")

    with SeseThreadPool(max_workers=10) as pool:
        for index, url in enumerate(image_urls):
            image_name = "%05d.jpg" % index
            image_path = image_temp_dir_path + "/" + image_name

            # 加入下载线程
            pool.submit(_download_file, image_path, url, True, progress)
            image_index = image_index + 1

        try:
            pool.wait_all()

        except Exception as e:
            SESE_TRACE(LOG_ERROR, f"下载失败！info: {e}")
            if progress:
                progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_ERROR)
            raise

    SESE_PRINT("下载完成！")
    if progress:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_PROCESS)

    # 图片下载完成，打包成漫画文件
    make_comic(save_dir, comic_title, image_temp_dir_path, chapter.metadata)

    if progress:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)


def download_task(task_name, func, *args):
    download_manager.add_task(task_name, func, *args)
    # SESE_PRINT('download task running!')
