from threading import Lock
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import functools
from typing import Callable
import inspect
import traceback
from core.utils.trace import *
from core.utils.file_utils import *
from core.utils.output import ProgressBar


class ProgressStatus:
    PROGRESS_STATUS_WAIT = "WAIT"  # 等待中
    PROGRESS_STATUS_DOWNLOADING = "DOWNLOAD"  # 下载中
    PROGRESS_STATUS_PROCESS = "PROCESS"  # 处理中
    PROGRESS_STATUS_DOWNLOAD_OK = "OK"  # 下载完成
    PROGRESS_STATUS_DOWNLOAD_ERROR = "ERR"  # 下载失败


class FileDLProgress:
    """单个文件下载进度"""

    def __init__(self, name, total=0):
        self.filename: str = name  # 文件名
        self.downloaded: int = 0  # 已下载字节数
        self.total: int = total  # 总字节数（未知时为-1）
        self.percent: float = 0.0  # 下载百分比
        self.speed: float = 0.0  # 下载速度（KB/s）
        self.status: str = ProgressStatus.PROGRESS_STATUS_WAIT  # 状态: ProgressStatus
        self.error: str = ""  # 错误信息
        self._lock = Lock()

    def update(self, **kwargs):
        """线程安全的更新方法"""
        need_update_percent = False
        with self._lock:  # 需要添加线程锁
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)
                if k == "total":
                    need_update_percent = True
                if k == "downloaded":
                    need_update_percent = True

            if need_update_percent:
                if self.total != 0:
                    self.percent = (self.downloaded / self.total) * 100


class TaskDLProgress:
    """下载任务进度"""

    def __init__(self, name):
        self.name = name  # 下载任务名
        self.total_progress = FileDLProgress(name)  # 记录下载任务总进度
        self.progress_dict: dict[str, FileDLProgress] = {}  # 记录每个文件的进度
        self.progress_count = 0  # 文件总数
        self.finish_count = 0  # 文件下载完成数
        self.current_progress: FileDLProgress | None = None  # 当前显示的文件进度
        self.bar: ProgressBar | None = None  # 进度条
        self._lock = Lock()
        self._update_lock = Lock()

    def init_progress(self):
        if not self.bar:
            self.bar = ProgressBar(self.name, 0, False)

    def set_progress_count(self, count):
        """设置下载文件总数，必须在add_progress之前调用"""
        self.progress_count = count

    def add_progress(self, file_name: str, total: int = 0):
        """
        添加新文件下载进度
        Args:
            file_name: 下载文件名
            total: 下载文件总大小，可以暂时缺省，之后使用 set_total 设置

        Returns:

        """
        with self._lock:
            file_base_name = get_file_basename(file_name)
            if file_base_name not in self.progress_dict:
                if len(self.progress_dict) < self.progress_count:
                    progress = FileDLProgress(file_base_name, total=total)
                    self.progress_dict[file_base_name] = progress
                    # SESE_TRACE(LOG_INFO, f"add_progress[{len(self.progress_dict)}][{file_base_name}], total[{total}]")
                    progress.update(total=total)
                    self.total_progress.update(total=self.total_progress.total + total)
                else:
                    SESE_TRACE(LOG_WARNING, f"Download file count over preset! Set {self.progress_count} but \
                                                add {len(self.progress_dict) + 1}")

    def get_progress(self, file_name: str) -> FileDLProgress:
        """获取指定文件的进度对象"""
        with self._lock:
            file_base_name = get_file_basename(file_name)
            return self.progress_dict.get(file_base_name)

    def _update_progress(self, file_name: str | None = None, downloaded=0):
        """
        更新下载任务总进度
        Args:
            file_name: 更新进度的文件名
            downloaded: 更新后的已下载数据量

        """
        with self._update_lock:
            BAR_SHOW_TOTAL_PROGRESS = False  # True: 显示所有下载文件的总进度，  False: 显示当前正在下载的文件的进度

            if file_name:
                # SESE_PRINT(f"_update_progress[{file_name}]")
                file_base_name = get_file_basename(file_name)
                progress = self.get_progress(file_base_name)

                if progress:
                    new_downloaded = downloaded - progress.downloaded
                    progress.update(downloaded=downloaded)
                    self.total_progress.update(downloaded=self.total_progress.downloaded + new_downloaded)

                    # SESE_PRINT(f"update progress [{file_base_name}] {downloaded}/{progress.total}")
                    if progress.total == progress.downloaded:
                        self.finish_count = self.finish_count + 1

                    if self.current_progress is None and progress.downloaded > 0:
                        # 如果current_progress为None，则将current_progress设置成当前更新文件
                        self.current_progress = progress

                    if self.current_progress is not None and \
                            file_base_name == self.current_progress.filename:
                        # 如果更新的文件是current_progress记录的文件，则更新进度
                        if not BAR_SHOW_TOTAL_PROGRESS:
                            self.bar.set_total(self.current_progress.total)
                            self.bar.set_downloaded(self.current_progress.downloaded)

                        if self.current_progress.total == self.current_progress.downloaded:
                            # 判断current_progress记录文件是否下载完成，若是，则置None
                            self.current_progress = None

                    if BAR_SHOW_TOTAL_PROGRESS:
                        self.bar.set_total(self.total_progress.total)
                        self.bar.set_downloaded(self.total_progress.downloaded)

            # 更新标题
            title_max_len = 32
            status = f"[{self.total_progress.status}]"
            statistics = f"[{self.finish_count}/{self.progress_count}] "
            total_len = len(self.name) + len(statistics) + len(status)
            if total_len <= title_max_len:
                title = status + statistics + self.name
            else:
                title = status + statistics + self.name[:title_max_len - (len(statistics) + len(status)) - 3] + "..."

            self.bar.set_description(title)

    def set_status(self, status):
        """设置任务状态"""
        self.total_progress.update(status=status)
        self._update_progress()

        if status == ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK:
            self.bar.close()
        elif status == ProgressStatus.PROGRESS_STATUS_DOWNLOAD_ERROR:
            self.bar.close()

    def set_total(self, file_name, total):
        file_base_name = get_file_basename(file_name)
        progress = self.get_progress(file_base_name)
        if progress:
            progress.update(total=total)
            self.total_progress.update(total=sum(p.total for p in self.progress_dict.values()))

    def set_downloaded(self, file_name, downloaded):
        """
        更新进度
        Args:
            file_name:  文件名
            downloaded: 已下载数据量
        """
        self._update_progress(file_name, downloaded)

    def update(self, file_name, n):
        """
        更新进度
        Args:
            file_name: 文件名
            n: 新增数据量
        """
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
        self.thread = None


class DownloadManager:
    """下载任务管理器"""

    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.tasks: list[DownloadTask] = []
        self.id_to_task = {}  # 新增ID映射字典
        self._tasks_lock = Lock()
        self.task_pool = ThreadPoolExecutor(max_workers=max_concurrent)

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
        wrapped_func = self._wrap_download_func(func, task.task_progress)

        task.thread = self.task_pool.submit(wrapped_func, *args)
        task.thread.add_done_callback(self._handle_exception)
        SESE_PRINT(f"创建下载任务[task_id: {task_id}, name: {name}]")
        return task

    @staticmethod
    def _wrap_download_func(
            original_func: Callable,
            progress: TaskDLProgress
    ) -> Callable:
        """向original_func中注入关键字参数progress（如果函数支持）"""
        sig = inspect.signature(original_func)

        # 检查参数是否存在
        param = sig.parameters.get('progress')
        if param and (
                param.default != inspect.Parameter.empty  # 有默认值
                or
                param.kind == param.KEYWORD_ONLY  # 仅关键字
        ):
            # 使用 partial 绑定回调
            return functools.partial(
                original_func,
                progress=progress
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
        wait([task.thread for task in self.tasks], return_when=ALL_COMPLETED)
        self.task_pool.shutdown()

    def kill(self):
        self.task_pool.shutdown(wait=False)

    def all_done(self):
        return all(future.done() for future in [task.thread for task in self.tasks])


download_manager = DownloadManager(max_concurrent=3)
