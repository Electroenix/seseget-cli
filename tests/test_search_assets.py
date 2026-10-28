import pytest

from web_app.api import search as search_api


@pytest.mark.asyncio
async def test_cover_download_failure_is_non_fatal(monkeypatch):
    async def fail_download(*args, **kwargs):
        raise RuntimeError("cover failed")

    monkeypatch.setattr(search_api, "download_file", fail_download)

    result = await search_api.download_cover(
        "test-site", "cover.jpg", "https://example.test/cover.jpg"
    )

    assert result is False


@pytest.mark.asyncio
async def test_thumbnail_batch_failure_is_non_fatal(monkeypatch):
    async def fail_downloads(*args, **kwargs):
        raise RuntimeError("thumbnails failed")

    monkeypatch.setattr(search_api, "download_files_ex", fail_downloads)

    result = await search_api.download_thumbnails(
        "test-site",
        ["one.jpg", "two.jpg"],
        ["https://example.test/one.jpg", "https://example.test/two.jpg"],
    )

    assert result is False
