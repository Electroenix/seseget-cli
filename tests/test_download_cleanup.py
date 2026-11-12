import pytest

import seseget.request.downloadtask as downloadtask
from seseget.request.download_history import DownloadHistoryStore
from seseget.request.downloadtask import DownloadManager


def _manager(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)
    return manager, store


@pytest.mark.asyncio
async def test_failed_task_cleans_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr(downloadtask, "DATA_DIR", str(tmp_path))
    manager, store = _manager(tmp_path)
    video_dir = tmp_path / "video"
    video_dir.mkdir()
    (video_dir / "part.mp4").write_bytes(b"partial")

    task = manager.new_task("failed")
    task.track_dir(video_dir)

    async def fail(task):
        raise RuntimeError("boom")

    task.set_runner(fail)
    manager.start(task)

    with pytest.raises(RuntimeError):
        await task.asyncio_task

    assert not video_dir.exists()
    record = store.items[0]
    assert record["status"] == "failed"
    assert record["cleaned"] is True
    assert record["cleaned_bytes"] > 0


@pytest.mark.asyncio
async def test_success_does_not_clean_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr(downloadtask, "DATA_DIR", str(tmp_path))
    manager, store = _manager(tmp_path)
    video_dir = tmp_path / "video"
    video_dir.mkdir()
    (video_dir / "video.mp4").write_bytes(b"ok")

    task = manager.new_task("success")
    task.track_dir(video_dir)

    async def success(task):
        pass

    task.set_runner(success)
    manager.start(task)
    await task.asyncio_task

    assert video_dir.exists()
    assert store.items[0]["status"] == "success"
    assert store.items[0]["cleaned"] is False


@pytest.mark.asyncio
async def test_cleanup_refuses_paths_outside_data_dir(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(downloadtask, "DATA_DIR", str(data_dir))
    manager, store = _manager(tmp_path)

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_bytes(b"keep")

    task = manager.new_task("failed")
    task.track_dir(outside)

    async def fail(task):
        raise RuntimeError("boom")

    task.set_runner(fail)
    manager.start(task)

    with pytest.raises(RuntimeError):
        await task.asyncio_task

    assert outside.exists()
    assert store.items[0]["cleaned"] is False
    assert store.items[0]["cleaned_bytes"] == 0


@pytest.mark.asyncio
async def test_cleanup_can_be_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(downloadtask, "DATA_DIR", str(tmp_path))
    manager, store = _manager(tmp_path)
    video_dir = tmp_path / "video"
    video_dir.mkdir()
    (video_dir / "part.mp4").write_bytes(b"partial")

    task = manager.new_task("failed")
    task.track_dir(video_dir)

    async def fail(task):
        raise RuntimeError("boom")

    task.set_runner(fail)
    monkeypatch.setattr(
        downloadtask.DownloadManager, "_cleanup_enabled", staticmethod(lambda: False)
    )
    manager.start(task)

    with pytest.raises(RuntimeError):
        await task.asyncio_task

    assert video_dir.exists()
    assert store.items[0]["cleaned"] is False
