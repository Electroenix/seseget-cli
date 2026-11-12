import asyncio
from types import SimpleNamespace

import pytest

import seseget.output.comic as comic_output
import seseget.request.fetcher as fetcher_module
import seseget.request.task_downloader as task_downloader
from seseget.request.download_history import DownloadHistoryStore
from seseget.request.downloadtask import DownloadManager, FileDLProgress
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


def test_comic_dir_is_reused_without_suffix(tmp_path):
    class ComicDirFetcher(ComicFetcher):
        async def _fetch_info(self, url, **kwargs):
            return ComicInfo()

    ComicDirFetcher.site_dir = str(tmp_path)
    fetcher = ComicDirFetcher()

    first = ComicInfo()
    first.title = "Same Title"
    fetcher._prepare_comic_dir(first)
    assert first.comic_dir == str(tmp_path / "Same Title")

    (tmp_path / "Same Title" / "chapter.cbz").write_bytes(b"existing")

    second = ComicInfo()
    second.title = "Same Title"
    fetcher._prepare_comic_dir(second)

    assert second.comic_dir == first.comic_dir
    assert not (tmp_path / "Same Title_[1]").exists()


@pytest.mark.asyncio
async def test_comic_skips_existing_output_before_images(monkeypatch, tmp_path):
    monkeypatch.setattr(
        comic_output,
        "config",
        {"download": {"comic": {"format": ["cbz"]}}},
    )
    comic_dir = tmp_path / "Title"
    comic_dir.mkdir()
    (comic_dir / "Title_001.cbz").write_bytes(b"existing")

    comic_info = ComicInfo()
    comic_info.title = "Title"
    comic_info.comic_dir = str(comic_dir)
    chapter = SimpleNamespace(
        comic_info=comic_info,
        id=1,
        image_urls=["https://example.test/1.jpg"],
    )

    class FakeProgress:
        def __init__(self):
            self.statuses = []

        def set_status(self, status):
            self.statuses.append(status)

    class FakeTask:
        def __init__(self):
            self.task_progress = FakeProgress()

        def track_dir(self, path):
            raise AssertionError("skip path should not track artifacts")

    async def fail_download(*args, **kwargs):
        raise AssertionError("images should not be downloaded")

    monkeypatch.setattr(task_downloader, "download_comic_capter_images", fail_download)
    fetcher = DummyComic()
    task = FakeTask()

    await fetcher._download_task(task, "Title_001", chapter)

    assert task.task_progress.statuses == [FileDLProgress.Status.DOWNLOAD_OK]
    assert not (comic_dir / "img-1").exists()
