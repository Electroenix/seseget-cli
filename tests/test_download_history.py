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

    async def success(progress=None):
        progress.progress_count = 2
        progress.finish_count = 2
        return "ok"

    async def failure(progress=None):
        raise RuntimeError("network failed")

    success_task = await manager.create_task("success", success)
    await success_task.asyncio_task

    failure_task = await manager.create_task("failure", failure)
    with pytest.raises(RuntimeError):
        await failure_task.asyncio_task

    assert manager.tasks == []
    assert [item["name"] for item in store.items] == ["failure", "success"]
    assert store.items[0]["status"] == "failed"
    assert "network failed" in store.items[0]["error"]
    assert store.items[1]["status"] == "success"
    assert store.items[1]["file_count"] == 2


@pytest.mark.asyncio
async def test_manager_marks_error_status_as_failed(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)

    async def error_but_returns(progress=None):
        progress.total_progress.status = FileDLProgress.Status.DOWNLOAD_ERROR
        progress.total_progress.error = "disk full"

    task = await manager.create_task("error-status", error_but_returns)
    await task.asyncio_task

    assert store.items[0]["status"] == "failed"
    assert store.items[0]["error"] == "disk full"


@pytest.mark.asyncio
async def test_manager_finalizes_cancelled_task(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)
    started = asyncio.Event()

    async def pending(progress=None):
        started.set()
        await asyncio.Event().wait()

    task = await manager.create_task("cancelled", pending)
    await started.wait()
    task.asyncio_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task.asyncio_task

    assert store.items[0]["status"] == "cancelled"
    assert store.items[0]["error"] == "任务已取消"


@pytest.mark.asyncio
async def test_manager_history_pagination(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)
    for index in range(3):
        store.add(_record(index, f"2026-01-0{index + 1}T00:00:00+00:00"), max_items=200)

    items, total = manager.get_history(limit=1, offset=1)

    assert total == 3
    assert [item["id"] for item in items] == ["id-1"]
