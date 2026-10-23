import os

import pytest

import seseget.request.downloader as downloader


@pytest.mark.asyncio
async def test_m3u8_uses_isolated_temp_dir_and_ordered_concat(monkeypatch):
    concat_state = {}

    async def fake_get_ts_list(url):
        return ["https://example.test/1.ts", "https://example.test/2.ts"]

    async def fake_download_file(file_name, url, *args, **kwargs):
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "wb") as f:
            f.write(b"ts")

    def fake_exec_cmd(command):
        concat_path = command[command.index("-i") + 1]
        concat_state["concat_path"] = concat_path
        concat_state["temp_dir"] = os.path.dirname(concat_path)
        with open(concat_path, encoding="utf-8") as f:
            concat_state["content"] = f.read()
        return True

    monkeypatch.setattr(downloader, "_get_ts_list_from_m3u8", fake_get_ts_list)
    monkeypatch.setattr(downloader, "_download_file", fake_download_file)
    monkeypatch.setattr(downloader, "exec_cmd", fake_exec_cmd)

    result = await downloader.download_mp4_by_m3u8("output.mp4", "https://example.test/playlist.m3u8")

    assert result == 0
    assert concat_state["content"].splitlines() == [
        "file '00000001.ts'",
        "file '00000002.ts'",
    ]
    assert not os.path.exists(concat_state["temp_dir"])


@pytest.mark.asyncio
async def test_m3u8_empty_playlist_fails(monkeypatch):
    async def fake_get_ts_list(url):
        return []

    monkeypatch.setattr(downloader, "_get_ts_list_from_m3u8", fake_get_ts_list)

    with pytest.raises(ValueError, match="没有找到 ts 分片"):
        await downloader.download_mp4_by_m3u8("output.mp4", "https://example.test/playlist.m3u8")


@pytest.mark.asyncio
async def test_m3u8_ffmpeg_failure_cleans_temp_dir(monkeypatch):
    temp_dirs = []

    async def fake_get_ts_list(url):
        return ["https://example.test/1.ts"]

    async def fake_download_file(file_name, url, *args, **kwargs):
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "wb") as f:
            f.write(b"ts")

    def fake_exec_cmd(command):
        concat_path = command[command.index("-i") + 1]
        temp_dirs.append(os.path.dirname(concat_path))
        return False

    monkeypatch.setattr(downloader, "_get_ts_list_from_m3u8", fake_get_ts_list)
    monkeypatch.setattr(downloader, "_download_file", fake_download_file)
    monkeypatch.setattr(downloader, "exec_cmd", fake_exec_cmd)

    with pytest.raises(RuntimeError, match="ffmpeg 拼接 m3u8 失败"):
        await downloader.download_mp4_by_m3u8("output.mp4", "https://example.test/playlist.m3u8")

    assert temp_dirs
    assert not os.path.exists(temp_dirs[0])
