import asyncio

import pytest

from seseget.request.download_history import DownloadHistoryStore
from seseget.request.downloadtask import DownloadManager, FileDLProgress


def _record(index, finished_at):
    return {
        "id": f"id-{index}",
        "name": f"task-{index}",
        "status": "success",
        "finished_at": finished_at,
    }


def test_history_store_persists_and_trims(tmp_path):
    path = tmp_path / "history.json"
    store = DownloadHistoryStore(str(path))

    store.add(_record(1, "2026-01-01T00:00:00+00:00"), max_items=2)
    store.add(_record(2, "2026-01-02T00:00:00+00:00"), max_items=2)
    store.add(_record(3, "2026-01-03T00:00:00+00:00"), max_items=2)

    assert [item["id"] for item in store.items] == ["id-3", "id-2"]
    assert store.latest_id == "id-3"

    reloaded = DownloadHistoryStore(str(path))
    assert [item["id"] for item in reloaded.items] == ["id-3", "id-2"]


def test_history_store_handles_corrupt_json(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{not valid json", encoding="utf-8")

    store = DownloadHistoryStore(str(path))

    assert store.items == []
    assert store.latest_id is None


def test_history_store_clear(tmp_path):
    path = tmp_path / "history.json"
    store = DownloadHistoryStore(str(path))
    store.add(_record(1, "2026-01-01T00:00:00+00:00"), max_items=200)

    store.clear()

    assert store.items == []
    assert DownloadHistoryStore(str(path)).items == []


@pytest.mark.asyncio
async def test_manager_finalizes_success_and_failure(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)

    async def success(task):
        task.task_progress.progress_count = 2
        task.task_progress.finish_count = 2
        task.task_progress.total_progress.total = 2048
        return "ok"

    async def failure(task):
        raise RuntimeError("network failed")

    success_task = manager.new_task("success", site="bika")
    success_task.set_runner(success)
    manager.start(success_task)
    await success_task.asyncio_task
    assert success_task.state == "SUCCESS"

    failure_task = manager.new_task("failure")
    failure_task.set_runner(failure)
    manager.start(failure_task)
    with pytest.raises(RuntimeError):
        await failure_task.asyncio_task
    assert failure_task.state == "FAILED"

    assert manager.tasks == []
    assert [item["name"] for item in store.items] == ["failure", "success"]
    assert store.items[0]["status"] == "failed"
    assert "network failed" in store.items[0]["error"]
    assert store.items[1]["status"] == "success"
    assert store.items[1]["file_count"] == 2
    assert store.items[1]["site"] == "bika"
    assert store.items[1]["total_bytes"] == 2048


@pytest.mark.asyncio
async def test_manager_marks_error_status_as_failed(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)

    async def error_but_returns(task):
        task.task_progress.total_progress.status = FileDLProgress.Status.DOWNLOAD_ERROR
        task.task_progress.total_progress.error = "disk full"

    task = manager.new_task("error-status")
    task.set_runner(error_but_returns)
    manager.start(task)
    await task.asyncio_task

    assert store.items[0]["status"] == "failed"
    assert store.items[0]["error"] == "disk full"
    assert task.state == "FAILED"


@pytest.mark.asyncio
async def test_manager_finalizes_cancelled_task(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)
    started = asyncio.Event()

    async def pending(task):
        started.set()
        await asyncio.Event().wait()

    task = manager.new_task("cancelled")
    task.set_runner(pending)
    manager.start(task)
    await started.wait()
    task.asyncio_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task.asyncio_task

    assert store.items[0]["status"] == "cancelled"
    assert store.items[0]["error"] == "任务已取消"
    assert task.state == "CANCELLED"


@pytest.mark.asyncio
async def test_manager_history_pagination(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)
    for index in range(3):
        store.add(_record(index, f"2026-01-0{index + 1}T00:00:00+00:00"), max_items=200)

    items, total = manager.get_history(limit=1, offset=1)

    assert total == 3
    assert [item["id"] for item in items] == ["id-1"]
