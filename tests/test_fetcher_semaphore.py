import asyncio

import pytest

from seseget.request.fetcher import ComicFetcher, ComicInfo, VideoFetcher, VideoInfo
from seseget.sites.twitter import TwitterFetcher


class DummyVideo(VideoFetcher):
    site_dir = "."

    def _make_save_dir(self, info):
        pass

    async def _fetch_info(self, url, **kwargs):
        return VideoInfo()


class DummyComic(ComicFetcher):
    site_dir = "."

    def _make_save_dir(self, info):
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
    assert fetcher.task_semaphore._value == 2


@pytest.mark.asyncio
async def test_video_download_concurrency_is_limited():
    fetcher = DummyVideo(max_tasks=2)
    active = 0
    peak = 0

    async def process(video_info, progress=None):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1

    fetcher._download_process = process
    await asyncio.gather(
        *(fetcher._download_process_with_semaphore(VideoInfo()) for _ in range(6))
    )

    assert peak <= 2
    assert fetcher.task_semaphore._value == 2


@pytest.mark.asyncio
async def test_fetcher_semaphore_released_on_fetch_error():
    fetcher = DummyVideo(max_tasks=1)

    async def fail(url, **kwargs):
        raise RuntimeError("fetch failed")

    fetcher._fetch_info = fail
    with pytest.raises(RuntimeError):
        await fetcher.download("url", no_download=True)

    assert fetcher.task_semaphore._value == 1


@pytest.mark.asyncio
async def test_comic_downloads_are_serialized():
    fetcher = DummyComic(max_tasks=1)
    active = 0
    peak = 0

    async def process(title, chapter, progress=None):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1

    fetcher._download_process = process
    chapters = [object(), object(), object()]
    await asyncio.gather(
        *(
            fetcher._download_process_with_semaphore("comic", chapter)
            for chapter in chapters
        )
    )

    assert peak == 1
    assert fetcher.task_semaphore._value == 1


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
    assert fetcher.task_semaphore._value == 2
