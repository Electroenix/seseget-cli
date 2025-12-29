import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Callable, Optional, List

from .trace import *


class SeseThreadPool:
    def __init__(self, max_workers: int, name: Optional[str] = None):
        self._max_workers = max_workers
        self._name = name or f"SeseThreadPool-{id(self)}"
        self._threads_list: List[Future] = []
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=self._name
        )
        self._done_callback: Optional[Callable[[Future], None]] = None
        self._is_shutdown = False

    def _handle_exception(self, future: Future):
        """处理完成任务的异常"""
        if future.exception():
            exc = future.exception()
            SESE_TRACE(LOG_DEBUG, f"任务异常: {future}! info: {exc}")

    def submit(self, fn, /, *args, **kwargs) -> Future:
        """提交任务到线程池"""
        if self._is_shutdown:
            raise RuntimeError("Cannot submit to a shutdown thread pool")

        thread: Future = self._pool.submit(fn, *args, **kwargs)

        if self._done_callback:
            thread.add_done_callback(self._done_callback)
        else:
            thread.add_done_callback(self._handle_exception)

        SESE_TRACE(LOG_DEBUG, f"提交任务 {thread}")
        self._threads_list.append(thread)
        return thread

    def close(self, wait: bool = True, cancel_futures: bool = False):
        """关闭线程池

        Args:
            wait: 是否等待已提交的任务完成
            cancel_futures: 是否取消尚未开始的任务
        """
        if self._is_shutdown:
            return

        if cancel_futures:
            for f in self._threads_list:
                if not f.done():
                    f.cancel()
                    SESE_TRACE(LOG_DEBUG, f"取消任务: {f}")

        self._pool.shutdown(wait=wait)
        self._is_shutdown = True

    def wait_all(self, raise_exceptions: bool = True):
        """等待所有任务完成

        Args:
            raise_exceptions: 是否在遇到异常时抛出
        """
        if self._is_shutdown:
            return

        try:
            for t in as_completed(self._threads_list):
                exception = t.exception()
                if exception and raise_exceptions:
                    raise exception
        finally:
            # 等待所有任务完成后关闭线程池
            self.close(wait=True, cancel_futures=True)

    def set_done_callback(self, fn: Callable[[Future], None]):
        """设置任务完成回调函数"""
        self._done_callback = fn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close(wait=True)
        return False

    @property
    def is_shutdown(self) -> bool:
        """检查线程池是否已关闭"""
        return self._is_shutdown

    @property
    def all_done(self) -> bool:
        return all(future.done() for future in self._threads_list)
