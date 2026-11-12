from ..downloader import DownloadObserver
from ..downloadtask import DownloadTask, TaskDLProgress


class TaskProgressObserver:
    """把底层下载事件转换为 TaskDLProgress 更新。"""

    def __init__(self, progress: TaskDLProgress):
        self.progress = progress

    def on_start(self, file_name: str, total: int) -> None:
        self.progress.add_progress(file_name, total=total)

    def on_chunk(self, file_name: str, size: int) -> None:
        self.progress.update(file_name, size)

    def on_skip(self, file_name: str, total: int) -> None:
        self.progress.add_progress(file_name, total=total)
        self.progress.update(file_name, total)

    def on_progress(self, file_name: str, downloaded: int, total: int) -> None:
        self.progress.add_progress(file_name, total=total)
        self.progress.set_downloaded(file_name, downloaded)

    def on_status(self, status: str) -> None:
        self.progress.set_status(status)


def observer_for(task: DownloadTask) -> DownloadObserver:
    return TaskProgressObserver(task.task_progress)
