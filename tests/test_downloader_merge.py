import os

import pytest

import seseget.request.downloader as downloader
from seseget.request.downloadtask import FileDLProgress


class FakeProgress:
    def __init__(self):
        self.statuses = []

    def init_progress(self):
        pass

    def set_progress_count(self, _count):
        pass

    def set_status(self, status):
        self.statuses.append(status)


def _prepare_download(monkeypatch, tmp_path, exec_result):
    output = tmp_path / "output.mp4"
    cache_files = []

    async def fake_download_files(file_names, urls, **_kwargs):
        cache_files.extend(file_names)
        for file_name in file_names:
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            with open(file_name, "wb") as f:
                f.write(b"data")
        return 0

    def fake_exec_cmd(_command):
        if exec_result:
            output.write_bytes(b"merged")
        else:
            output.write_bytes(b"partial")
        return exec_result

    monkeypatch.setattr(downloader, "_download_files", fake_download_files)
    monkeypatch.setattr(downloader, "exec_cmd", fake_exec_cmd)
    return output, cache_files


@pytest.mark.asyncio
async def test_merge_success_removes_cache(monkeypatch, tmp_path):
    output, cache_files = _prepare_download(monkeypatch, tmp_path, True)
    progress = FakeProgress()

    result = await downloader.download_mp4_by_merge_video_audio(
        str(output), "https://example.test/video.mp4", "https://example.test/audio.mp3", {}, progress
    )

    assert result == 0
    assert output.read_bytes() == b"merged"
    assert progress.statuses[-1] == FileDLProgress.Status.DOWNLOAD_OK
    assert cache_files
    assert not os.path.exists(os.path.join(tmp_path, "cache"))


@pytest.mark.asyncio
async def test_merge_failure_keeps_cache_and_removes_partial_output(monkeypatch, tmp_path):
    output, cache_files = _prepare_download(monkeypatch, tmp_path, False)
    progress = FakeProgress()

    result = await downloader.download_mp4_by_merge_video_audio(
        str(output), "https://example.test/video.mp4", "https://example.test/audio.mp3", {}, progress
    )

    assert result == -1
    assert not output.exists()
    assert progress.statuses[-1] == FileDLProgress.Status.DOWNLOAD_ERROR
    assert os.path.isdir(os.path.join(tmp_path, "cache"))
    assert cache_files


@pytest.mark.asyncio
async def test_merge_missing_output_is_failure(monkeypatch, tmp_path):
    output = tmp_path / "output.mp4"

    async def fake_download_files(_file_names, _urls, **_kwargs):
        return 0

    def fake_exec_cmd(_command):
        return True

    monkeypatch.setattr(downloader, "_download_files", fake_download_files)
    monkeypatch.setattr(downloader, "exec_cmd", fake_exec_cmd)
    progress = FakeProgress()

    result = await downloader.download_mp4_by_merge_video_audio(
        str(output), "https://example.test/video.mp4", "https://example.test/audio.mp3", {}, progress
    )

    assert result == -1
    assert progress.statuses[-1] == FileDLProgress.Status.DOWNLOAD_ERROR
