from threading import Lock
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import functools
from typing import Callable, TypeAlias, Protocol
import inspect
from core.utils.trace import *
from core.utils.file_utils import *
import traceback


class FileDLProgress:
    """单个文件下载进度"""
    def __init__(self):
        self.downloaded: int = 0  # 已下载字节数
        self.total: int = 0  # 总字节数（未知时为-1）
        self.percent: float = 0.0  # 下载百分比
        self.speed: float = 0.0  # 下载速度（KB/s）
        self.status: str = "pending"  # 状态：pending/running/paused/error/completed
        self.error: str = ""  # 错误信息
        self._lock = Lock()

    def update(self, **kwargs):
        """线程安全的更新方法"""
        need_update_percent = False
        with self._lock:  # 需要添加线程锁
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)
                if k == "downloaded" or k == "total":
                    need_update_percent = True

            if need_update_percent:
                if self.total != 0:
                    self.percent = (self.downloaded / self.total) * 100


class TaskDLProgress:
    """下载任务进度"""
    def __init__(self):
        self.progress = FileDLProgress()  # 记录下载任务总进度
        self.file_progress_dict: dict[str, FileDLProgress] = {}  # 记录每个文件的进度
        self._lock = Lock()

    def add_progress(self, file_name: str):
        """添加新文件下载进度"""
        with self._lock:
            file_base_name = get_file_basename(file_name)
            if file_base_name not in self.file_progress_dict:
                self.file_progress_dict[file_base_name] = FileDLProgress()
                SESE_TRACE(LOG_DEBUG, f"add_progress[{file_base_name}]")

    def get_progress(self, file_name: str) -> FileDLProgress:
        """获取指定文件的进度对象"""
        with self._lock:
            file_base_name = get_file_basename(file_name)
            return self.file_progress_dict.get(file_base_name)

    def _update_progress_by_file_progress_dict(self):
        """遍历所有文件进度更新下载任务总进度"""
        total = 0
        downloaded = 0
        for k, v in self.file_progress_dict.items():
            total = total + v.total
            downloaded = downloaded + v.downloaded

        self.progress.update(downloaded=downloaded, total=total)

    def update(self, file_name, **kwargs):
        """下载进度更新

        Args:
            file_name: if None: 更新下载任务总进度, if not None: 更新文件下载进度.

        """
        if file_name is None:
            # 更新下载任务进度
            progress = self.progress
            progress.update(**kwargs)
        else:
            # 更新文件下载进度
            file_base_name = get_file_basename(file_name)
            if file_base_name not in self.file_progress_dict:
                self.add_progress(file_base_name)  # 添加新文件进度对象

            progress = self.get_progress(file_base_name)

            if 'new_downloaded' in kwargs:  # new_downloaded更新至downloaded
                new_downloaded = kwargs.pop('new_downloaded')
                downloaded = progress.downloaded + new_downloaded
                kwargs["downloaded"] = downloaded

            progress.update(**kwargs)
            self._update_progress_by_file_progress_dict()

    def progress_callback(self, file_name: str = None, /, *, downloaded: int = None, new_downloaded: int = None, total: int = None, status: str = None):
        """下载进度更新回调

        Args:
            file_name: if None: 更新下载任务总进度, if not None: 更新文件下载进度
            downloaded: 已下载大小
            new_downloaded: 新增下载大小
            total: 总大小
            status: 下载状态

        """

        if downloaded is not None:
            self.update(file_name, downloaded=downloaded)
        if new_downloaded is not None:
            self.update(file_name, new_downloaded=new_downloaded)
        if total is not None:
            self.update(file_name, total=total)
        if status is not None:
            self.update(file_name, status=status)


class ProgressCallback(Protocol):
    def __call__(self, file_name: str = None, /, *, downloaded: int = None, new_downloaded: int = None, total: int = None, status: str = None) -> None:
        ...


class DownloadTask:
    """下载任务，记录任务id, name和进度"""

    def __init__(self, task_id: str, name: str):
        self.id: str = task_id
        self.name: str = name
        self.task_progress: TaskDLProgress = TaskDLProgress()


class DownloadManager:
    """下载任务管理器"""

    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.tasks: list[DownloadTask] = []
        self.id_to_task = {}  # 新增ID映射字典
        self._tasks_lock = Lock()
        self.task_pool = ThreadPoolExecutor(max_workers=max_concurrent)
        self.threads = []

        # ID生成配置
        self._id_counter = 0
        self._id_lock = Lock()  # ID生成专用锁

    def _generate_task_id(self):
        """生成唯一任务ID（递增数字+UUID混合模式）"""
        with self._id_lock:
            self._id_counter += 1
            return f"{self._id_counter}-{uuid.uuid4().hex[:6]}"

    def add_task(self, name, func, *args):
        """创建下载任务"""
        task_id = self._generate_task_id()
        task = DownloadTask(task_id, name)

        with self._tasks_lock:
            self.tasks.append(task)
            self.id_to_task[task_id] = task  # 维护ID映射

        # 使用functools.partial包装函数和参数
        # 自动注入进度回调参数（如果函数支持）
        wrapped_func = self._wrap_download_func(func, task.task_progress.progress_callback)

        thread = self.task_pool.submit(wrapped_func, *args)
        thread.add_done_callback(self._handle_exception)
        self.threads.append(thread)
        SESE_PRINT(f"创建下载任务[task_id: {task_id}, name: {name}]")
        return task

    @staticmethod
    def _wrap_download_func(
            original_func: Callable,
            progress_callback: ProgressCallback
    ) -> Callable:
        """向original_func中注入关键字参数progress_callback（如果函数支持）"""
        sig = inspect.signature(original_func)

        # 检查参数是否存在
        param = sig.parameters.get('progress_callback')
        if param and (
                param.default != inspect.Parameter.empty  # 有默认值
                or
                param.kind == param.KEYWORD_ONLY  # 仅关键字
        ):
            # 使用 partial 绑定回调
            return functools.partial(
                original_func,
                progress_callback=progress_callback
            )
        else:
            return original_func

    @staticmethod
    def _handle_exception(future):
        """处理完成任务的异常"""
        if future.exception():
            exc = future.exception()
            SESE_TRACE(LOG_ERROR, "下载任务异常! info: %s\r\n\r\nTraceback:\r\n%s" %
                       (exc, ''.join(traceback.format_tb(exc.__traceback__))))

    def get_task_by_id(self, task_id):
        """根据任务ID获取任务实例"""
        with self._tasks_lock:
            return self.id_to_task.get(task_id)

    def get_all_tasks(self):
        """获取所有任务列表的副本"""
        with self._tasks_lock:
            return self.tasks.copy()

    def wait_finish(self):
        wait(self.threads, return_when=ALL_COMPLETED)
        self.task_pool.shutdown()

    def kill(self):
        self.task_pool.shutdown(wait=False)

    def all_done(self):
        return all(future.done() for future in self.threads)


download_manager = DownloadManager(max_concurrent=3)
