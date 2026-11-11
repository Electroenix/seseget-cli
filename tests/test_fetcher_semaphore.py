import asyncio

import pytest

import seseget.request.fetcher as fetcher_module
from seseget.request.download_history import DownloadHistoryStore
from seseget.request.downloadtask import DownloadManager
from seseget.request.errors import SiteParseError
from seseget.request.fetcher import ComicFetcher, ComicInfo, VideoFetcher, VideoInfo
from seseget.sites.twitter import TwitterFetcher


class DummyVideo(VideoFetcher):
    site_dir = "."

    def _prepare_dir(self, info):
        pass

    async def _fetch_info(self, url, **kwargs):
        return VideoInfo()


class DummyComic(ComicFetcher):
    site_dir = "."

    def _prepare_comic_dir(self, info):
        pass

    async def _fetch_info(self, url, **kwargs):
        return ComicInfo()


@pytest.mark.asyncio
async def test_video_fetch_concurrency_is_limited():
    fetcher = DummyVideo(max_tasks=2)
    active = 0
    peak = 0

    async def fetch(url, **kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return VideoInfo()

    fetcher._fetch_info = fetch
    await asyncio.gather(
        *(fetcher.download(str(i), no_download=True) for i in range(6))
    )

    assert peak <= 2
    assert fetcher.fetch_semaphore._value == 2


@pytest.mark.asyncio
async def test_fetcher_semaphore_released_on_fetch_error():
    fetcher = DummyVideo(max_tasks=1)

    async def fail(url, **kwargs):
        raise RuntimeError("fetch failed")

    fetcher._fetch_info = fail
    with pytest.raises(SiteParseError) as exc_info:
        await fetcher.download("url", no_download=True)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert fetcher.fetch_semaphore._value == 1


@pytest.mark.asyncio
async def test_twitter_fetch_concurrency_is_limited():
    active = 0
    peak = 0

    class DummyTwitter(TwitterFetcher):
        async def _get_video_info_list_by_yt_dlp(self, url):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.02)
            active -= 1
            return []

    fetcher = DummyTwitter(max_tasks=2)
    await asyncio.gather(
        *(fetcher.download(str(i), no_download=True) for i in range(5))
    )

    assert peak <= 2
    assert fetcher.fetch_semaphore._value == 2


@pytest.mark.asyncio
async def test_manager_limits_concurrent_tasks(tmp_path):
    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=2, history_store=store)
    active = 0
    peak = 0

    async def runner(task):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1

    tasks = []
    for index in range(6):
        task = manager.new_task(f"task-{index}")
        task.set_runner(runner)
        tasks.append(manager.start(task))

    await asyncio.gather(*(task.asyncio_task for task in tasks))

    assert peak <= 2
    assert manager.tasks == []
    assert len(store.items) == 6


@pytest.mark.asyncio
async def test_video_download_starts_task_and_waits(monkeypatch, tmp_path):
    fetcher = DummyVideo()
    info = VideoInfo()
    info.name = "video"
    info.metadata.series = "series"

    async def fetch(url, **kwargs):
        return info

    def prepare(info):
        info.video_dir = str(tmp_path / "video")

    async def write_outputs(task, info):
        pass

    async def download_media(task, info):
        pass

    fetcher._fetch_info = fetch
    fetcher._prepare_dir = prepare
    fetcher._write_outputs = write_outputs
    fetcher._download_media = download_media

    store = DownloadHistoryStore(str(tmp_path / "history.json"))
    manager = DownloadManager(max_concurrent=1, history_store=store)
    monkeypatch.setattr(fetcher_module, "download_manager", manager)

    await fetcher.download("url")

    assert len(manager.tasks) == 1
    await manager.wait_all()

    assert manager.tasks == []
    assert store.items[0]["status"] == "success"
