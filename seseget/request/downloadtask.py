import asyncio
import uuid
import functools
from datetime import datetime, timezone
from typing import Callable
import inspect
import traceback

from ..config.config_manager import config
from ..utils.trace import logger
from ..utils.file_utils import get_file_basename
from ..utils.output import ProgressBar
from ..config import settings
from .download_history import DownloadHistoryStore

DEFAULT_MAX_HISTORY = 200


class FileDLProgress:
    """单文件下载进度"""

    class Status:
        WAIT = "WAIT"  # 等待中
        DOWNLOADING = "DOWNLOAD"  # 下载中
        PROCESS = "PROCESS"  # 处理中
        DOWNLOAD_OK = "OK"  # 下载完成
        DOWNLOAD_ERROR = "ERR"  # 下载失败

    def __init__(self, name, total=0):
        self.filename: str = name  # 文件名
        self.downloaded: int = 0  # 已下载字节数
        self.total: int = total  # 总字节数
        self.percent: float = 0.0  # 下载百分比
        self.speed: float = 0.0  # 下载速度（KB/s）
        self.status: str = FileDLProgress.Status.WAIT  # 状态: FileDLProgress.Status
        self.error: str = ""  # 错误信息

    def update(self, **kwargs):
        """更新对象属性"""
        need_update_percent = False
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            if k in ("total", "downloaded"):
                need_update_percent = True

        if need_update_percent and self.total != 0:
            self.percent = (self.downloaded / self.total) * 100


class TaskDLProgress:
    """下载任务进度

    下载任务包含一个总进度 total_progress，和一个用于存放任务中每个文件进度的列表 progress_dict，
    所有进度都采用FileDLProgress对象存储状态

    1, 对象初始化完成后首先需要调用 init_progress，这会创建一个进度条，显示在终端中，

    2, 调用 set_progress_count，设置任务中下载文件的总数，

    3, 每当有一个新文件开始下载时，都应该调用 add_progress 创建一个新文件的进度对象，加入到 progress_dict中，

    4, 通过 update (或 set_downloaded )更新每个文件的下载进度，

    5, 每当任务状态发生变化时，需要通过 set_status 修改任务状态
    """

    def __init__(self, name):
        self.name = name
        self.total_progress = FileDLProgress(name)
        self.progress_dict: dict[str, FileDLProgress] = {}
        self.progress_count = 0
        self.finish_count = 0
        self.current_progress: FileDLProgress | None = None
        self.bar: ProgressBar | None = None

    def init_progress(self):
        if not self.bar:
            self.bar = ProgressBar(self.name, 0, not settings.PROGRESS_BAR_ENABLED)

    def set_progress_count(self, count):
        """设置下载文件总数，必须在add_progress之前调用"""
        self.progress_count = count

    def add_progress(self, file_name: str, total: int = 0):
        """
        添加新文件下载进度
        Args:
            file_name: 下载文件名
            total: 下载文件总大小
        """
        file_base_name = get_file_basename(file_name)
        if file_base_name not in self.progress_dict:
            if len(self.progress_dict) < self.progress_count:
                progress = FileDLProgress(file_base_name, total=total)
                self.progress_dict[file_base_name] = progress
                progress.update(total=total)
                self.total_progress.update(total=self.total_progress.total + total)
            else:
                logger.warning(f"Download file count over preset! Set {self.progress_count} but "
                               f"add {len(self.progress_dict) + 1}")

    def get_progress(self, file_name: str) -> FileDLProgress | None:
        """获取指定文件的进度对象"""
        file_base_name = get_file_basename(file_name)
        return self.progress_dict.get(file_base_name)

    @property
    def progress_bar(self) -> ProgressBar:
        if self.bar is None:
            self.init_progress()
        if self.bar is None:
            raise RuntimeError("进度条初始化失败")
        return self.bar

    def _update_progress(self, file_name: str | None = None, downloaded=0):
        """
        更新下载任务总进度
        Args:
            file_name: 更新进度的文件名
            downloaded: 更新后的已下载数据量
        """
        BAR_SHOW_TOTAL_PROGRESS = False

        if file_name:
            file_base_name = get_file_basename(file_name)
            progress = self.get_progress(file_base_name)

            if progress:
                new_downloaded = downloaded - progress.downloaded
                progress.update(downloaded=downloaded)
                self.total_progress.update(downloaded=self.total_progress.downloaded + new_downloaded)

                if progress.total == progress.downloaded:
                    self.finish_count = self.finish_count + 1

                if self.current_progress is None and progress.downloaded > 0:
                    self.current_progress = progress

                if self.current_progress is not None and \
                        file_base_name == self.current_progress.filename:
                    if not BAR_SHOW_TOTAL_PROGRESS:
                        self.progress_bar.set_total(self.current_progress.total)
                        self.progress_bar.set_downloaded(self.current_progress.downloaded)

                    if self.current_progress.total == self.current_progress.downloaded:
                        self.current_progress = None

                if BAR_SHOW_TOTAL_PROGRESS:
                    self.progress_bar.set_total(self.total_progress.total)
                    self.progress_bar.set_downloaded(self.total_progress.downloaded)

        # 更新标题
        title_max_len = 32
        status = f"[{self.total_progress.status}]"
        statistics = f"[{self.finish_count}/{self.progress_count}] "
        total_len = len(self.name) + len(statistics) + len(status)
        if total_len <= title_max_len:
            title = status + statistics + self.name
        else:
            title = status + statistics + self.name[:title_max_len - (len(statistics) + len(status)) - 3] + "..."

        self.progress_bar.set_description(title)

    def set_status(self, status):
        """设置任务状态"""
        self.total_progress.update(status=status)
        self._update_progress()

        if status == FileDLProgress.Status.DOWNLOAD_OK:
            self.progress_bar.close()
        elif status == FileDLProgress.Status.DOWNLOAD_ERROR:
            self.progress_bar.close()

    def set_total(self, file_name, total):
        """设置文件总大小"""
        file_base_name = get_file_basename(file_name)
        progress = self.get_progress(file_base_name)
        if progress:
            progress.update(total=total)
            total_sum = sum(p.total for p in self.progress_dict.values())
            self.total_progress.update(total=total_sum)

    def set_downloaded(self, file_name, downloaded):
        """更新进度"""
        self._update_progress(file_name, downloaded)

    def update(self, file_name, n):
        """更新进度（增量）"""
        file_base_name = get_file_basename(file_name)
        progress = self.get_progress(file_base_name)
        if progress:
            downloaded = progress.downloaded + n
            self._update_progress(file_name, downloaded)


class DownloadTask:
    """下载任务，记录任务id, name和进度"""

    def __init__(self, task_id: str, name: str):
        self.id: str = task_id
        self.name: str = name
        self.task_progress: TaskDLProgress = TaskDLProgress(name)
        self.asyncio_task: asyncio.Task | None = None
        self.started_at: datetime | None = None
        self.finalized: bool = False


class DownloadManager:
    """下载任务管理器"""

    def __init__(self, max_concurrent=3, history_store: DownloadHistoryStore | None = None):
        self.max_concurrent = max_concurrent
        self.tasks: list[DownloadTask] = []
        self.id_to_task: dict[str, DownloadTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._id_counter = 0
        self.history_store = history_store or DownloadHistoryStore()
        self.history_store.trim(self.get_history_limit())

    def _generate_task_id(self):
        self._id_counter += 1
        return f"{self._id_counter}-{uuid.uuid4().hex[:6]}"

    def get_history_limit(self) -> int:
        """读取可配置的下载历史保留条数，非法配置回退到默认值。"""
        try:
            value = config["download"].get("max_history", DEFAULT_MAX_HISTORY)
            return max(1, int(value))
        except (KeyError, TypeError, ValueError):
            return DEFAULT_MAX_HISTORY

    def get_history(self, limit: int = DEFAULT_MAX_HISTORY, offset: int = 0):
        """返回历史记录切片和总条数。"""
        max_items = self.get_history_limit()
        if len(self.history_store.items) > max_items:
            self.history_store.trim(max_items)
        limit = max(1, min(int(limit), max_items))
        offset = max(0, int(offset))
        return self.history_store.items[offset:offset + limit], len(self.history_store.items)

    def clear_history(self):
        self.history_store.clear()

    @property
    def latest_history_id(self) -> str | None:
        return self.history_store.latest_id

    def _finalize_task(self, task: DownloadTask, status: str, error: str | None = None):
        """把终态任务写入历史，并从活动任务中移除。"""
        if task.finalized:
            return
        task.finalized = True

        finished_at = datetime.now(timezone.utc)
        started_at = task.started_at or finished_at
        progress = task.task_progress

        if (
            status == "success"
            and progress.total_progress.status == FileDLProgress.Status.DOWNLOAD_ERROR
        ):
            status = "failed"
            error = error or progress.total_progress.error or "下载失败"

        record = {
            "id": task.id,
            "name": task.name,
            "status": status,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration": round((finished_at - started_at).total_seconds(), 2),
            "file_count": progress.progress_count,
            "file_finish_count": progress.finish_count,
            "progress": round(progress.total_progress.percent, 2),
            "error": error or "",
        }
        self.history_store.add(record, self.get_history_limit())

        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.id_to_task.pop(task.id, None)

    def _wrap_download_func(self, original_func: Callable, progress: TaskDLProgress) -> Callable:
        """向original_func中注入关键字参数progress（如果函数支持）"""
        sig = inspect.signature(original_func)

        param = sig.parameters.get('progress')
        if param and (param.default != inspect.Parameter.empty or param.kind == param.KEYWORD_ONLY):
            return functools.partial(original_func, progress=progress)
        else:
            return original_func

    async def create_task(self, name, func, *args):
        """创建异步下载任务"""
        task_id = self._generate_task_id()
        task = DownloadTask(task_id, name)

        self.tasks.append(task)
        self.id_to_task[task_id] = task

        wrapped_func = self._wrap_download_func(func, task.task_progress)

        async def _run_with_semaphore():
            status = "failed"
            error = None
            try:
                async with self._semaphore:
                    task.started_at = datetime.now(timezone.utc)
                    result = await wrapped_func(*args)
                status = "success"
                return result
            except asyncio.CancelledError:
                status = "cancelled"
                error = "任务已取消"
                raise
            except Exception as exc:
                error = str(exc) or exc.__class__.__name__
                logger.error("下载任务异常! traceback:\r\n%s" %
                             ''.join(traceback.format_exc()))
                raise
            finally:
                self._finalize_task(task, status, error)

        asyncio_task = asyncio.create_task(_run_with_semaphore())
        task.asyncio_task = asyncio_task

        logger.debug(f"创建下载任务[task_id: {task_id}, name: {name}]")
        return task

    def get_task_by_id(self, task_id):
        return self.id_to_task.get(task_id)

    def get_all_tasks(self):
        return self.tasks.copy()

    async def wait_all(self):
        """等待所有任务完成"""
        pending = [t.asyncio_task for t in self.tasks if t.asyncio_task and not t.asyncio_task.done()]
        if pending:
            results = await asyncio.gather(*pending, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"下载任务异常! info: {r}")

    def all_done(self):
        """检查是否所有任务都完成"""
        return all(
            t.asyncio_task and t.asyncio_task.done()
            for t in self.tasks
            if t.asyncio_task
        )

    async def shutdown(self):
        """关闭管理器，取消所有未完成的任务"""
        for task in self.tasks:
            if task.asyncio_task and not task.asyncio_task.done():
                task.asyncio_task.cancel()
        self.tasks.clear()
        self.id_to_task.clear()


# 全局下载管理器实例
download_manager = DownloadManager(max_concurrent=3)
