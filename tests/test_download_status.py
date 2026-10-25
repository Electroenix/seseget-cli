import asyncio
from types import SimpleNamespace

import pytest

from web_app.api import download as download_api


def _task(task_id: str, name: str, percent: float):
    total = SimpleNamespace(percent=percent, speed=0, status="DOWNLOAD")
    progress = SimpleNamespace(
        name=name,
        total_progress=total,
        progress_count=2,
        finish_count=1,
    )
    return SimpleNamespace(id=task_id, task_progress=progress)


class FakeManager:
    def __init__(self, tasks):
        self.tasks = tasks
        self.latest_history_id = None


@pytest.mark.asyncio
async def test_emit_download_status_only_active_newest_first(monkeypatch):
    fake_manager = FakeManager([_task("old", "old-task", 10), _task("new", "new-task", 20)])
    events = []

    async def fake_emit(event, data=None):
        events.append((event, data))

    monkeypatch.setattr(download_api, "download_manager", fake_manager)
    monkeypatch.setattr(download_api.sio, "emit", fake_emit)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(download_api.emit_download_status(), timeout=0.05)

    status_events = [data for event, data in events if event == "download_status"]
    assert len(status_events) == 1
    assert [item["id"] for item in status_events[0]] == ["new", "old"]
    assert status_events[0][0]["file_count"] == 2
    assert status_events[0][0]["file_finish_count"] == 1
