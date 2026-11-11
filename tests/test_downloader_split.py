import pytest

import seseget.request.downloader as downloader
import seseget.request.task_downloader as task_downloader


class FakeResponse:
    status_code = 200
    headers = {"Content-Length": "3"}

    def __init__(self):
        self.closed = False

    async def aiter_content(self):
        yield b"abc"

    def raise_for_status(self):
        pass

    def close(self):
        self.closed = True


class RecordingObserver:
    def __init__(self):
        self.started = []
        self.chunks = []
        self.skipped = []

    def on_start(self, file_name, total):
        self.started.append((file_name, total))

    def on_chunk(self, file_name, size):
        self.chunks.append((file_name, size))

    def on_skip(self, file_name, total):
        self.skipped.append((file_name, total))

    def on_progress(self, file_name, downloaded, total):
        pass

    def on_status(self, status):
        pass


def test_core_downloader_does_not_import_task_models():
    assert "TaskDLProgress" not in vars(downloader)
    assert "FileDLProgress" not in vars(downloader)
    assert not hasattr(downloader, "download_mp4")


@pytest.mark.asyncio
async def test_download_file_notifies_observer(monkeypatch, tmp_path):
    response = FakeResponse()

    async def fake_request(*args, **kwargs):
        return response

    monkeypatch.setattr(downloader.session_manager, "request", fake_request)
    observer = RecordingObserver()
    target = tmp_path / "file.bin"

    result = await downloader._download_file(
        str(target), "https://example.test/file", observer=observer
    )

    assert result == 0
    assert target.read_bytes() == b"abc"
    assert observer.started == [(str(target), 3)]
    assert observer.chunks == [(str(target), 3)]
    assert response.closed


def test_task_progress_observer_maps_events():
    class FakeProgress:
        def __init__(self):
            self.calls = []

        def add_progress(self, file_name, total=0):
            self.calls.append(("add", file_name, total))

        def update(self, file_name, size):
            self.calls.append(("update", file_name, size))

        def set_downloaded(self, file_name, downloaded):
            self.calls.append(("set_downloaded", file_name, downloaded))

        def set_status(self, status):
            self.calls.append(("status", status))

    progress = FakeProgress()
    observer = task_downloader.TaskProgressObserver(progress)

    observer.on_start("a.mp4", 10)
    observer.on_chunk("a.mp4", 4)
    observer.on_progress("a.mp4", 6, 10)
    observer.on_skip("a.mp4", 10)
    observer.on_status("DOWNLOAD")

    assert progress.calls == [
        ("add", "a.mp4", 10),
        ("update", "a.mp4", 4),
        ("add", "a.mp4", 10),
        ("set_downloaded", "a.mp4", 6),
        ("add", "a.mp4", 10),
        ("update", "a.mp4", 10),
        ("status", "DOWNLOAD"),
    ]
