from flask import request, Blueprint

from seseget.request.fetcher import FetcherRegistry, VideoFetcher, ComicFetcher
from seseget.request.downloadtask import download_manager
from .response import ResponseCode, ApiResponse
from .. import socketio
from ..utils import run_async

download_bp = Blueprint('api/download', __name__)


@download_bp.route('', methods=['POST'])
def download():
    data = request.json
    print("data: ", data)

    site = data.get("station")
    url = data.get("url")
    chapters = data.get("chapters")

    if site:
        fetcher = FetcherRegistry.get_fetcher(site)
        if isinstance(fetcher, VideoFetcher):
            if url:
                run_async(fetcher.download(url))
            elif chapters and len(chapters) > 0:
                for chapter_url in chapters:
                    run_async(fetcher.download(chapter_url))
            else:
                response = ApiResponse(
                    code=ResponseCode.NOT_FOUND,
                    message="Error",
                    data={}
                )
                return response.to_response()

        elif isinstance(fetcher, ComicFetcher):
            if url and chapters:
                run_async(fetcher.download(url, chapter_id_list=chapters))
            else:
                response = ApiResponse(
                    code=ResponseCode.NOT_FOUND,
                    message="Error",
                    data={}
                )
                return response.to_response()

        response = ApiResponse(
            code=ResponseCode.SUCCESS,
            message="Success",
            data={}
        )
        return response.to_response()

    else:
        response = ApiResponse(
            code=ResponseCode.NOT_FOUND,
            message="Error",
            data={}
        )
        return response.to_response()


# --- SocketIO: 下载状态推送 ---
def emit_download_status():
    """后台任务：每秒通过 WebSocket 推送下载任务状态"""
    while True:
        tasks_info = []
        for task in download_manager.tasks:
            progress = task.task_progress
            tasks_info.append({
                "name": progress.name,
                "progress": progress.total_progress.percent,
                "speed": progress.total_progress.speed,
                "status": progress.total_progress.status,
                "file_count": progress.progress_count,
                "file_finish_count": progress.finish_count,
            })
        socketio.emit('download_status', tasks_info)
        socketio.sleep(1)
