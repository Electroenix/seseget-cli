import os
import sys
import time
import re
import shutil
import threading
import copy
from curl_cffi import requests
from urllib.parse import urlparse
from typing import Dict, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.utils.trace import *
from core.request import downloadtask as dltask
from core.request.downloadtask import TaskDLProgress, ProgressStatus
from core.metadata.comic import comic_to_epub
from core.config.config_manager import config
from core.utils.file_utils import get_file_basename


class SessionManager:
    """智能 Session 管理器，按请求主机自动分配独立 Session"""

    def __init__(self):
        # 存储不同主机的 Session 对象 {host: Session}
        self._sessions: Dict[str, requests.Session] = {}
        # 线程锁确保线程安全
        self._lock = threading.Lock()
        # 各主机的预定义配置 {host: {config_key: value}}
        self._host_configs: Dict[str, dict] = {}

    def register_host_config(self, host: str, **config):
        """为指定主机注册配置（如 headers、auth、proxies）"""
        with self._lock:
            self._host_configs[host] = config

    def _get_session_for_host(self, host: str) -> requests.Session:
        """获取或创建指定主机的 Session"""
        with self._lock:
            if host not in self._sessions:
                # 创建新 Session 并应用配置
                session = requests.Session()
                # 应用预注册的主机配置
                config = self._host_configs.get(host, {})
                for key, value in config.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                # 配置连接池（可按需调整）
                # adapter = HTTPAdapter(
                #     pool_connections=5,
                #     pool_maxsize=10,
                #     max_retries=3
                # )
                # session.mount('https://', adapter)
                # session.mount('http://', adapter)
                self._sessions[host] = session
            # PRINTLOG("当前session列表：", list(self._sessions.keys()))
            return self._sessions[host]

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发起请求，自动路由到对应主机的 Session"""
        parsed_url = urlparse(url)
        host = parsed_url.netloc  # 提取主机名（如 'api.example.com'）
        session = self._get_session_for_host(host)
        # 发起请求（可在此处添加统一异常处理）
        return session.request(method, url, **kwargs)

    def close_all(self):
        """关闭所有 Session 释放资源"""
        with self._lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()


ss_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}
# request_session = requests.Session()
ss_session = SessionManager()


def request(method, url, **kwargs):
    """发送单个请求"""
    if "headers" not in kwargs:
        kwargs["headers"] = copy.copy(ss_headers)
    if "proxies" not in kwargs:
        proxy_config = config["common"]["proxy"]
        if proxy_config["proxy_enable"] and proxy_config["address"]:
            proxies = {
                "http": proxy_config["address"],
                "https": proxy_config["address"],
            }
            kwargs["proxies"] = copy.copy(proxies)
            SESE_TRACE(LOG_DEBUG, f'proxy["{proxy_config["address"]}"]')
    if "impersonate" not in kwargs:
        kwargs["impersonate"] = "chrome110"

    retry_times = 0
    retry_max = 3
    response = None
    while True:
        try:
            response = ss_session.request(method, url, **kwargs)
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


def _download_file(file_name, url, bar=False, auto_retry=True, retry_max=5,
                   progress: TaskDLProgress = None, headers=None):
    """下载单个文件"""
    retry_times = 0
    if headers is None:
        headers = copy.copy(ss_headers)

    while True:
        try:
            with open(file_name, 'ab') as f:
                f_size = os.stat(file_name).st_size

                proxies = None
                proxy_config = config["common"]["proxy"]
                if proxy_config["proxy_enable"] and proxy_config["address"]:
                    proxies = {
                        "http": proxy_config["address"],
                        "https": proxy_config["address"],
                    }
                    SESE_TRACE(LOG_DEBUG, f'proxy["{proxy_config["address"]}"]')

                response = ss_session.request("HEAD", url=url, headers=headers, stream=True, proxies=proxies)

                if int(response.headers['Content-Length']) <= 0:
                    SESE_TRACE(LOG_DEBUG, "资源Content-Length大小错误-%d" % int(response.headers['Content-Length']))
                    return -1
                if f_size == int(response.headers['Content-Length']):
                    # 文件已存在，直接返回
                    SESE_TRACE(LOG_DEBUG, "检测到文件(%s)已存在" % file_name)
                    if progress is not None:
                        progress.add_progress(file_name, total=f_size)
                        progress.update(file_name, f_size)
                    return 0
                elif f_size > int(response.headers['Content-Length']):
                    # 文件大小错误，删除文件
                    SESE_TRACE(LOG_ERROR, "文件大小错误，删除文件(f_size:%d, Content-Length:%d)" %
                               (f_size, int(response.headers['Content-Length'])))
                    f.close()
                    os.remove(file_name)
                    continue

                # 设置从断点开始继续下载
                headers['Range'] = 'bytes=%d-' % f_size

                response = ss_session.request("GET", url=url, headers=headers, stream=True, proxies=proxies)
                response.raise_for_status()

                total_size = int(response.headers['Content-Length'])
                read_size = 0

                if progress is not None:
                    progress.add_progress(file_name, total=total_size)

                # for data in response.iter_content(chunk_size=1024):
                for data in response.iter_content():  # curl_cffi not accept chunk_size
                    size = f.write(data)
                    read_size = read_size + size
                    if progress is not None:
                        progress.update(file_name, size)

                break
        except Exception as result:
            if auto_retry:
                if retry_times < retry_max:
                    SESE_TRACE(LOG_ERROR, 'Error! info: %s' % result)
                    SESE_PRINT("GET %s Failed, Retry(%d)..." % (url, retry_times))
                    retry_times = retry_times + 1
                    time.sleep(5)
                    continue
                else:
                    return -1
            else:
                SESE_TRACE(LOG_ERROR, 'Error! info: %s' % result)
                retry = input('下载失败，是否重新下载(y/n)')
                if retry == 'y':
                    continue
                else:
                    return -1

    return 0


def _download_files(file_name_list: list[str], url_list: list[str],
                    progress: TaskDLProgress = None, headers=None):
    """下载多个文件"""
    if len(file_name_list) != len(url_list):
        SESE_TRACE(LOG_ERROR, "文件与下载地址数量不匹配！")
        return -1

    if headers is None:
        headers = copy.copy(ss_headers)

    threads_list = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        index = 0
        for file_name in file_name_list:
            url = url_list[index]

            # 创建下载任务
            threads_list.append(
                pool.submit(_download_file, file_name, url, True, True, 5, progress, headers))

            index = index + 1

        SESE_PRINT("已提交所有下载任务！")

        while True:
            # 检查所有任务是否完成
            all_done = all(future.done() for future in threads_list)
            if all_done:
                break
            time.sleep(1)

    SESE_PRINT("全部文件下载完成！")
    return 0


def download_file(file_name, url):
    """下载单个文件"""
    result = _download_file(file_name, url)
    return result


def download_mp4(filename, url, progress: TaskDLProgress = None):
    """下载mp4视频"""
    progress.set_progress_count(1)
    progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)

    result = _download_file(filename, url, bar=True, progress=progress)

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
    cmd = f'ffmpeg -hide_banner -i "{video_path}" -i "{audio_path}" -c:v copy -c:a aac -strict experimental "{filename}"'
    # 调用命令
    os.system(cmd)

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
    ts_threads_list = []

    if progress is not None:
        progress.set_progress_count(len(ts_list))
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)

    with ThreadPoolExecutor(max_workers=10) as pool:
        for ts_url in ts_list:
            ts_index = ts_index + 1
            f_ts_name = '%08d.ts' % ts_index

            if not os.path.exists('ts_temp'):
                os.mkdir('ts_temp')

            # 加入下载线程
            ts_threads_list.append(
                pool.submit(_download_file, 'ts_temp/%s' % f_ts_name, ts_url, False, True, 5, None, None))

            with open('ts_temp/ts_files_list.txt', 'a') as f_ts_files_list:
                f_ts_files_list.write('file \'%s\'\r\n' % f_ts_name)

        # 监测下载线程状态
        totle_cnt = len(ts_threads_list)
        finish_cnt = 0

        for thread in as_completed(ts_threads_list):
            finish_cnt = finish_cnt + 1
            SESE_PRINT('下载ts文件中(%d/%d)' % (finish_cnt, totle_cnt), end="\r")

    SESE_PRINT('下载完成!')
    if progress:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_PROCESS)

    # ffmpeg拼接ts文件，保存为mp4
    os.system('ffmpeg -f concat -safe 0 -i "ts_temp/ts_files_list.txt" -c copy "%s"' % filename)
    shutil.rmtree('ts_temp')

    if progress:
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)
    return 0


# 下载漫画
# dir - 漫画保存目录
#    目录结构
#        |- dir/  漫画系列名
#            |- series_title_001.epub  保存的epub格式的漫画
#            |- series_title_002.epub
#            |- series_title_xxx.epub
#            |- chapter_title/  以章节名命名的文件夹，临时存放下载的图片，转换成epub格式后就会被删除
#                |- 00001.jpg
#                |- 00002.jpg
#                |- xxxxx.jpg
def download_epub_by_images(file_name, image_urls, metadata, progress: TaskDLProgress = None):
    image_index = 1
    threads_list = []
    comic_dir = os.path.dirname(file_name)
    comic_title = os.path.splitext(file_name)[0].split("/")[-1]
    image_temp_dir_path = comic_dir + "/" + comic_title

    if not os.path.exists(image_temp_dir_path):
        os.mkdir(image_temp_dir_path)

    if progress is not None:
        progress.set_progress_count(len(image_urls))
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)

    with ThreadPoolExecutor(max_workers=10) as pool:
        for index, url in enumerate(image_urls):
            image_name = "%05d.jpg" % index
            image_path = image_temp_dir_path + "/" + image_name

            # 加入下载线程
            threads_list.append(pool.submit(_download_file, image_path, url, False, True, 5, progress, None))
            image_index = image_index + 1

        # 监测下载线程状态
        totle_cnt = len(threads_list)
        finish_cnt = 0

        for thread in as_completed(threads_list):
            if thread.result() == 0:
                finish_cnt = finish_cnt + 1
            # SESE_PRINT("%03d/%03d" % (finish_cnt, totle_cnt), end="\n")

    if finish_cnt == totle_cnt:
        SESE_PRINT("下载完成！")
    else:
        SESE_PRINT("下载失败！")
        if progress:
            progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_ERROR)
        return

    if progress:
        # progress.set_status(ProgressStatus.PROGRESS_STATUS_PROCESS)
        progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)

    # 下载完成，生成epub文件
    comic_to_epub(file_name, image_temp_dir_path, metadata)

    # if progress:
    #     progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)


def download_task(task_name, func, *args):
    dltask.download_manager.add_task(task_name, func, *args)
    # SESE_PRINT('download task running!')
