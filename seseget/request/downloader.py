import asyncio
import os
from typing import Protocol

from ..utils.trace import logger
from .requests import session_manager

DOWNLOAD_RETRY_INTERVAL = 2


class DownloadObserver(Protocol):
    """下载过程观察者，用于把 I/O 与任务进度解耦。"""

    def on_start(self, file_name: str, total: int) -> None: ...

    def on_chunk(self, file_name: str, size: int) -> None: ...

    def on_skip(self, file_name: str, total: int) -> None: ...

    def on_progress(self, file_name: str, downloaded: int, total: int) -> None: ...

    def on_status(self, status: str) -> None: ...


async def _download_file(
    file_name,
    url,
    auto_retry=True,
    observer: DownloadObserver | None = None,
    **kwargs,
):
    """
    下载单个文件

    整体流程：
      1. 检查本地文件状态（存在？大小？） → 决定是否断点续传
      2. 发起 GET 请求（stream=True）
      3. 根据响应状态码判断：全新下载 / 续传 / 已完成 / 文件损坏
      4. 流式读取响应体，逐 chunk 写入文件 + 通知 observer
      5. 异常时重试（最多 3 次）

    Args:
        file_name: 文件保存完整路径
        url: 下载地址
        auto_retry: 下载异常时是否自动重试（最多 3 次）
        observer: 可选的下载进度观察者
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
                logger.debug("[response open]")

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
                            if observer is not None:
                                observer.on_skip(file_name, f_size)
                            response.close()
                            logger.debug("[response close]")
                            return 0
                        else:
                            logger.warning(f"文件大小错误，删除文件重新下载，file: {file_name}, "
                                           f"(f_size:{f_size}, remote_file_size:{remote_file_size})")

                    # 删除损坏/不完整的文件，回到 while 顶部重新下载
                    os.remove(file_name)
                    response.close()
                    logger.debug("[response close]")
                    continue

                # 其他错误状态码
                response.raise_for_status()

                if observer is not None:
                    observer.on_start(file_name, total_size)

                with open(file_name, file_mode) as f:
                    async for data in response.aiter_content():
                        size = f.write(data)
                        read_size = read_size + size
                        if observer is not None:
                            observer.on_chunk(file_name, size)

                    break

            except Exception:
                if response:
                    logger.debug(f"Error! response header: {response.headers}")
                raise

            finally:
                response.close()
                logger.debug("[response close]")

        except Exception as result:
            if auto_retry:
                if retry_times < retry_max:
                    logger.debug('Error! info: %s' % result)
                    logger.debug("GET %s Failed, Retry(%d)..." % (url, retry_times))
                    retry_times = retry_times + 1
                    await asyncio.sleep(DOWNLOAD_RETRY_INTERVAL)
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


async def _download_files(
    file_name_list: list[str],
    url_list: list[str],
    *,
    max_workers=10,
    observer: DownloadObserver | None = None,
    **kwargs,
):
    """
    下载多个文件

    Args:
        file_name_list: 文件保存路径列表
        url_list: 下载地址列表
        max_workers: 最大同时下载数
        observer: 可选的下载进度观察者
        **kwargs: 传递给单个下载请求的附加参数
    """
    if len(file_name_list) != len(url_list):
        logger.error("文件与下载地址数量不匹配！")
        return -1

    semaphore = asyncio.Semaphore(max_workers)

    async def _download_with_semaphore(file_name, url):
        async with semaphore:
            return await _download_file(file_name, url, True, observer, **kwargs)

    tasks = [_download_with_semaphore(f, u) for f, u in zip(file_name_list, url_list, strict=True)]
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


# 普通下载接口，不包含任务进度


async def download_file(file_name, url):
    """下载单个文件"""
    return await _download_file(file_name, url)


async def download_files(file_name_list: list[str], url_list: list[str]):
    """下载多个文件"""
    return await _download_files(file_name_list, url_list)
