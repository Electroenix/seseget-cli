import asyncio
import logging

from fastapi import APIRouter, Request

from seseget.request.fetcher import FetcherRegistry, VideoFetcher, ComicFetcher
from seseget.request.downloadtask import download_manager
from .response import ResponseCode, ApiResponse
from .. import sio

logger = logging.getLogger(__name__)

router = APIRouter()


async def _safe_download(fetcher, url, **kwargs):
    try:
        await fetcher.download(url, **kwargs)
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")


@router.post("")
async def download(request: Request):
    data = await request.json()
    print("data: ", data)

    site = data.get("station")
    url = data.get("url")
    chapters = data.get("chapters")

    if site:
        fetcher = FetcherRegistry.get_fetcher(site)
        if isinstance(fetcher, VideoFetcher):
            if url:
                asyncio.create_task(_safe_download(fetcher, url))
            elif chapters and len(chapters) > 0:
                for chapter_url in chapters:
                    asyncio.create_task(_safe_download(fetcher, chapter_url))
            else:
                return ApiResponse(code=ResponseCode.NOT_FOUND, message="Error")

        elif isinstance(fetcher, ComicFetcher):
            if url and chapters:
                asyncio.create_task(
                    _safe_download(fetcher, url, chapter_id_list=chapters)
                )
            else:
                return ApiResponse(code=ResponseCode.NOT_FOUND, message="Error")

        return ApiResponse(code=ResponseCode.SUCCESS, message="Success")

    else:
        return ApiResponse(code=ResponseCode.NOT_FOUND, message="Error")


async def emit_download_status():
    """后台任务：每秒通过 WebSocket 推送下载任务状态"""
    while True:
        tasks_info = []
        for task in download_manager.tasks:
            progress = task.task_progress
            tasks_info.append(
                {
                    "name": progress.name,
                    "progress": progress.total_progress.percent,
                    "speed": progress.total_progress.speed,
                    "status": progress.total_progress.status,
                    "file_count": progress.progress_count,
                    "file_finish_count": progress.finish_count,
                }
            )
        await sio.emit("download_status", tasks_info)
        await asyncio.sleep(1)
