import asyncio
import os
import re
import shutil

from .downloadtask import TaskDLProgress, FileDLProgress, download_manager
from .requests import session_manager
from ..utils.file_utils import get_file_basename
from ..utils.subprocess_utils import exec_cmd
from ..utils.trace import logger


async def _download_file(file_name, url, auto_retry=True, progress: TaskDLProgress = None, **kwargs):
    """
    下载单个文件

    整体流程：
      1. 检查本地文件状态（存在？大小？） → 决定是否断点续传
      2. 发起 GET 请求（stream=True）
      3. 根据响应状态码判断：全新下载 / 续传 / 已完成 / 文件损坏
      4. 流式读取响应体，逐 chunk 写入文件 + 更新进度
      5. 异常时重试（最多 3 次）

    Args:
        file_name: 文件保存完整路径
        url: 下载地址
        auto_retry: 下载异常时是否自动重试（最多 3 次）
        progress: 控制下载进度的 TaskDLProgress 对象
        **kwargs: 附加参数，传递给异步 HTTP 请求（headers, proxy 等）
    """
    retry_max = 3
    retry_times = 0

    while True:
        try:
            f_size = 0
            if os.path.exists(file_name):
                f_size = os.path.getsize(file_name)

            if f_size > 0:
                # 本地已有部分数据 → 设置 Range 头，从断点位置继续下载
                if "headers" not in kwargs:
                    kwargs["headers"] = {}
                kwargs["headers"]['Range'] = 'bytes=%d-' % f_size
            elif "headers" in kwargs and "Range" in kwargs["headers"]:
                # 本地文件不存在但传入了 Range → 清理掉（从头下载）
                kwargs["headers"].pop("Range")

            logger.debug(f"request [{url}]")
            response = await session_manager.request("GET", url=url, stream=True, **kwargs)
            if response:
                logger.debug(f"[response open]")

            total_size = 0
            read_size = 0
            file_mode = ''

            try:
                if response.status_code == 200:
                    # 200 OK：服务器返回完整文件（不支持续传 或 第一次下载）
                    file_mode = 'wb'
                    logger.debug(f"respone[200], Content-Length: {response.headers['Content-Length']}")
                    total_size = int(response.headers['Content-Length'])

                elif response.status_code == 206:
                    # 206 Partial Content：服务器接受了 Range 请求，从断点续传
                    file_mode = 'ab'    # 追加模式，不覆盖已有数据
                    logger.debug(f"respone[206], Content-Length: {response.headers['Content-Length']}")
                    total_size = f_size + int(response.headers['Content-Length'])

                elif response.status_code == 416:
                    # 416 Range Not Satisfiable：请求的 Range 超出服务器文件范围
                    if 'Content-Range' not in response.headers:
                        logger.warning(f"无法验证文件大小，删除文件重新下载，file: {file_name}")
                    else:
                        remote_file_size = int(response.headers['Content-Range'].split("/")[-1])
                        if f_size == remote_file_size:
                            logger.debug("检测到文件(%s)已存在" % file_name)
                            if progress is not None:
                                progress.add_progress(file_name, total=f_size)
                                progress.update(file_name, f_size)
                            response.close()
                            logger.debug(f"[response close]")
                            return 0
                        else:
                            logger.warning(f"文件大小错误，删除文件重新下载，file: {file_name}, "
                                           f"(f_size:{f_size}, remote_file_size:{remote_file_size})")

                    # 删除损坏/不完整的文件，回到 while 顶部重新下载
                    os.remove(file_name)
                    response.close()
                    logger.debug(f"[response close]")
                    continue

                # 其他错误状态码
                response.raise_for_status()

                if progress is not None:
                    progress.add_progress(file_name, total=total_size)

                with open(file_name, file_mode) as f:
                    async for data in response.aiter_content():
                        size = f.write(data)
                        read_size = read_size + size
                        if progress is not None:
                            progress.update(file_name, size)

                    break

            except Exception:
                if response:
                    logger.debug(f"Error! response header: {response.headers}")
                raise

            finally:
                response.close()
                logger.debug(f"[response close]")

        except Exception as result:
            if auto_retry:
                if retry_times < retry_max:
                    logger.debug('Error! info: %s' % result)
                    logger.debug("GET %s Failed, Retry(%d)..." % (url, retry_times))
                    retry_times = retry_times + 1
                    await asyncio.sleep(5)
                    continue
                else:
                    raise
            else:
                logger.error('Error! info: %s' % result)
                retry = input('下载失败，是否重新下载(y/n)')
                if retry == 'y':
                    continue
                else:
                    raise

    return 0


async def _download_files(file_name_list: list[str],
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
    """
    if len(file_name_list) != len(url_list):
        logger.error("文件与下载地址数量不匹配！")
        return -1

    semaphore = asyncio.Semaphore(max_workers)

    async def _download_with_semaphore(file_name, url):
        async with semaphore:
            return await _download_file(file_name, url, True, progress, **kwargs)

    tasks = [_download_with_semaphore(f, u) for f, u in zip(file_name_list, url_list)]
    logger.info("已提交所有下载任务！")

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"下载失败！info: {r}")
                raise r
        logger.info("全部文件下载完成！")
    except Exception as e:
        logger.error(f"下载失败！info: {e}")
        raise

    return 0


# 适配各种场景下的下载接口

async def download_file(file_name, url):
    """下载单个文件"""
    result = await _download_file(file_name, url)
    return result


async def download_file_ex(file_name: str,
                            url: str,
                            *,
                            progress: TaskDLProgress = None,
                            **kwargs):
    """下载单个文件"""
    result = await _download_file(file_name, url, True, progress, **kwargs)
    return result


async def download_files(file_name_list: list[str], url_list: list[str]):
    """下载多个文件"""
    result = await _download_files(file_name_list, url_list)
    return result


async def download_files_ex(file_name_list: list[str],
                             url_list: list[str],
                             *,
                             max_workers=10,
                             progress: TaskDLProgress = None,
                             **kwargs):
    """下载多个文件"""
    result = await _download_files(file_name_list,
                                    url_list,
                                    max_workers=max_workers,
                                    progress=progress,
                                    **kwargs)
    return result


async def download_mp4(filename, url, progress: TaskDLProgress = None):
    """下载mp4视频"""
    progress.init_progress()
    progress.set_progress_count(1)
    progress.set_status(FileDLProgress.Status.DOWNLOADING)

    result = await _download_file(filename, url, progress=progress)

    if result == 0:
        progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)
        logger.info(f"{get_file_basename(filename)} Download OK!")
    else:
        progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        logger.info(f"{get_file_basename(filename)} Download ERROR!")
    return result


async def download_mp4_by_merge_video_audio(filename, video_url, audio_url, headers,
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
    progress.set_status(FileDLProgress.Status.DOWNLOADING)
    if await _download_files(
            [audio_path, video_path],
            [audio_url, video_url],
            progress=progress,
            headers=headers) != 0:
        logger.error("download_files failed!")
        progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        return -1

    logger.info("开始合并音视频文件...")
    progress.set_status(FileDLProgress.Status.PROCESS)

    # ffmpeg 是 CPU 密集型子进程，放入线程池执行
    await asyncio.to_thread(
        exec_cmd,
        ["ffmpeg", "-hide_banner", "-i", f"{video_path}", "-i", f"{audio_path}", "-c:v", "copy", "-c:a", "aac",
         "-strict", "experimental", f"{filename}"]
    )

    logger.info(f"合并完成，保存在{filename}")
    progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)

    shutil.rmtree(cache_dir)
    logger.info(f"已删除缓存文件")

    return 0


async def _get_ts_list_from_m3u8(url):
    ts_list = []

    # 异步下载m3u8文件
    response = await session_manager.request("GET", url=url, stream=True)

    # m3u8文件中的uri
    uri_list = re.findall(r'(?<=\n)\w.*', response.text)
    for uri in uri_list:
        if '.m3u8' in uri:
            m3u8_url = url.rsplit('/', 1)[0] + '/' + uri
            ts_list = ts_list + await _get_ts_list_from_m3u8(m3u8_url)
        elif '.ts' in uri:
            ts_url = url.rsplit('/', 1)[0] + '/' + uri
            ts_list.append(ts_url)

    return ts_list


async def download_mp4_by_m3u8(filename, url, progress: TaskDLProgress = None):
    """下载m3u8文件，保存为mp4格式"""
    ts_list = await _get_ts_list_from_m3u8(url)
    ts_index = 0

    if progress is not None:
        progress.init_progress()
        progress.set_progress_count(len(ts_list))
        progress.set_status(FileDLProgress.Status.DOWNLOADING)

    semaphore = asyncio.Semaphore(10)

    async def _download_ts(ts_url, idx):
        f_ts_name = '%08d.ts' % idx
        if not os.path.exists('ts_temp'):
            os.mkdir('ts_temp')

        async with semaphore:
            await _download_file('ts_temp/%s' % f_ts_name, ts_url, True, None)

        with open('ts_temp/ts_files_list.txt', 'a') as f_ts_files_list:
            f_ts_files_list.write('file \'%s\'\r\n' % f_ts_name)

    tasks = []
    for idx, ts_url in enumerate(ts_list, start=1):
        tasks.append(_download_ts(ts_url, idx))

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"下载失败！info: {r}")
                if progress:
                    progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
                raise r
    except Exception as e:
        logger.error(f"下载失败！info: {e}")
        if progress:
            progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        raise

    logger.info('下载完成!')
    if progress:
        progress.set_status(FileDLProgress.Status.PROCESS)

    # ffmpeg拼接ts文件，保存为mp4
    await asyncio.to_thread(
        exec_cmd,
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", "ts_temp/ts_files_list.txt", "-c", "copy", filename]
    )
    shutil.rmtree('ts_temp')

    if progress:
        progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)
    return 0


async def download_comic_capter_images(save_dir: str, image_urls, progress: TaskDLProgress = None):
    """
    下载漫画章节
    Args:
        save_dir: 图片保存目录
        image_urls: 存放漫画图片的url列表
        progress: 控制下载进度的对象
    """
    image_index = 1

    if progress is not None:
        progress.init_progress()
        progress.set_progress_count(len(image_urls))
        progress.set_status(FileDLProgress.Status.DOWNLOADING)

    logger.debug(f"image_urls: {image_urls}")

    semaphore = asyncio.Semaphore(10)

    async def _download_image(index, url):
        image_name = "%05d.jpg" % index
        image_path = save_dir + "/" + image_name
        async with semaphore:
            await _download_file(image_path, url, True, progress)

    tasks = [_download_image(idx, url) for idx, url in enumerate(image_urls)]

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"下载失败！info: {r}")
                if progress:
                    progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
                raise r
    except Exception as e:
        logger.error(f"下载失败！info: {e}")
        if progress:
            progress.set_status(FileDLProgress.Status.DOWNLOAD_ERROR)
        raise

    logger.info("下载完成！")
    if progress:
        progress.set_status(FileDLProgress.Status.PROCESS)
