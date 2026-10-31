import asyncio
import logging

from fastapi import APIRouter, Request

from seseget.request.downloadtask import download_manager
from seseget.request.fetcher import ComicFetcher, FetcherRegistry, VideoFetcher

from .. import sio
from .response import ApiResponse, ResponseCode

logger = logging.getLogger(__name__)

router: APIRouter = APIRouter()


async def _safe_download(fetcher, url, **kwargs):
    try:
        await fetcher.download(url, **kwargs)
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")


@router.post("")
async def download(request: Request):
    data = await request.json()

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


@router.get("/history")
async def get_download_history(limit: int | None = None, offset: int = 0):
    """获取已结束的下载历史。"""
    effective_limit = download_manager.get_history_limit() if limit is None else limit
    items, total = download_manager.get_history(limit=effective_limit, offset=offset)
    return ApiResponse(
        data={
            "items": items,
            "total": total,
            "max_items": download_manager.get_history_limit(),
        }
    )


@router.delete("/history")
async def clear_download_history():
    """清空下载历史。"""
    try:
        download_manager.clear_history()
    except OSError as e:
        logger.error(f"清空下载历史失败: {e}")
        return ApiResponse(
            code=ResponseCode.SERVER_ERROR,
            message="清空下载历史失败",
        )
    return ApiResponse(code=ResponseCode.SUCCESS, message="Success")


async def emit_download_status():
    """后台任务：每秒通过 WebSocket 推送活动下载任务状态"""
    last_history_id = download_manager.latest_history_id
    while True:
        latest_history_id = download_manager.latest_history_id
        if latest_history_id != last_history_id:
            last_history_id = latest_history_id
            await sio.emit("download_finished", {"id": latest_history_id})

        tasks_info = []
        # 活动任务按创建顺序倒序，新任务排在列表最前面
        for task in reversed(list(download_manager.tasks)):
            progress = task.task_progress
            tasks_info.append(
                {
                    "id": task.id,
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
