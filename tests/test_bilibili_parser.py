from pathlib import Path

import pytest

from seseget.request.errors import SiteParseError
from seseget.sites.bilibili import (
    BilibiliFetcher,
    _extract_bvid,
    parse_play_urls,
    parse_video_detail,
    parse_video_page,
)

FIXTURE = Path(__file__).parent / "fixtures" / "bilibili" / "video.html"


def test_parse_video_page():
    html = FIXTURE.read_text(encoding="utf-8")

    page = parse_video_page(
        html,
        "https://www.bilibili.com/video/BV1test12345",
        expected_bvid="BV1test12345",
    )

    assert page.bvid == "BV1test12345"
    assert page.cid == "123456"
    assert page.info.metadata.title == "测试视频"
    assert page.info.metadata.author == "测试UP"
    assert page.info.metadata.public_time == "2024-01-01"
    assert page.info.metadata.tag_list == ["测试标签", "动画"]
    assert page.info.cover_url == "https://example.test/cover.jpg"
    assert page.info.video_view == "100"
    assert page.info.video_like == "20"


def test_parse_video_page_missing_state():
    with pytest.raises(SiteParseError, match="__INITIAL_STATE__"):
        parse_video_page("<html></html>", "https://www.bilibili.com/video/BV1test12345")


def test_parse_video_page_invalid_json():
    html = "<script>window.__INITIAL_STATE__={bad json}</script>"

    with pytest.raises(SiteParseError, match="JSON"):
        parse_video_page(html, "https://www.bilibili.com/video/BV1test12345")


def test_parse_video_page_bvid_mismatch():
    html = FIXTURE.read_text(encoding="utf-8")

    with pytest.raises(SiteParseError, match="不一致"):
        parse_video_page(
            html,
            "https://www.bilibili.com/video/BV1other12345",
            expected_bvid="BV1other12345",
        )


def test_extract_bvid_rejects_non_bv_url():
    with pytest.raises(SiteParseError, match="BV"):
        _extract_bvid("https://www.bilibili.com/video/av123")


def test_parse_play_urls():
    payload = {
        "code": 0,
        "data": {
            "dash": {
                "video": [{"baseUrl": "https://example.test/video.mp4"}],
                "audio": [{"base_url": "https://example.test/audio.mp4"}],
            }
        },
    }

    assert parse_play_urls(payload) == (
        "https://example.test/video.mp4",
        "https://example.test/audio.mp4",
    )


def test_parse_play_urls_api_error():
    with pytest.raises(SiteParseError, match="code=1"):
        parse_play_urls({"code": 1, "message": "error"})


def test_parse_play_urls_missing_dash():
    with pytest.raises(SiteParseError, match="dash"):
        parse_play_urls({"code": 0, "data": {}})


def test_parse_video_detail():
    payload = {
        "code": 0,
        "data": {
            "View": {
                "bvid": "BV1test12345",
                "cid": 123456,
                "title": "API 测试视频",
                "desc": "API 测试简介",
                "pubdate": 1704067200,
                "pic": "http://example.test/cover.jpg",
                "owner": {"name": "API 测试UP"},
                "stat": {
                    "view": 100,
                    "like": 20,
                    "coin": 10,
                    "favorite": 5,
                    "share": 2,
                },
            },
            "Tags": [{"tag_name": "API 标签"}],
        },
    }

    page = parse_video_detail(
        payload,
        "https://www.bilibili.com/video/BV1test12345",
        expected_bvid="BV1test12345",
    )

    assert page.bvid == "BV1test12345"
    assert page.cid == "123456"
    assert page.info.metadata.title == "API 测试视频"
    assert page.info.metadata.author == "API 测试UP"
    assert page.info.metadata.public_time == "2024-01-01"
    assert page.info.metadata.tag_list == ["API 标签"]
    assert page.info.cover_url == "https://example.test/cover.jpg"


def test_parse_video_detail_api_error():
    with pytest.raises(SiteParseError, match="code=-352"):
        parse_video_detail({"code": -352, "message": "risk control"})


@pytest.mark.asyncio
async def test_fetch_page_falls_back_to_html(monkeypatch):
    fetcher = BilibiliFetcher()
    html = FIXTURE.read_text(encoding="utf-8")

    async def fail_api(*_args, **_kwargs):
        raise SiteParseError("api unavailable")

    async def fallback_html(bvid, url):
        return parse_video_page(html, url, expected_bvid=bvid)

    monkeypatch.setattr(fetcher, "_fetch_api_page", fail_api)
    monkeypatch.setattr(fetcher, "_fetch_html_page", fallback_html)

    page = await fetcher._fetch_page(
        "BV1test12345",
        "https://www.bilibili.com/video/BV1test12345",
    )

    assert page.info.metadata.title == "测试视频"


def test_parse_video_page_missing_video_data():
    html = '<script>window.__INITIAL_STATE__={"bvid":"BV1test12345","cid":123}</script>'

    with pytest.raises(SiteParseError, match="videoData"):
        parse_video_page(html, "https://www.bilibili.com/video/BV1test12345")


def test_parse_video_detail_missing_view():
    with pytest.raises(SiteParseError, match="View"):
        parse_video_detail({"code": 0, "data": {}})


def test_parse_video_detail_empty_title():
    payload = {
        "code": 0,
        "data": {
            "View": {
                "bvid": "BV1test12345",
                "cid": 123,
                "title": "",
                "pic": "//example.test/cover.jpg",
                "pubdate": 1704067200,
                "owner": {"name": "UP"},
                "stat": {},
            }
        },
    }

    with pytest.raises(SiteParseError, match="View.title"):
        parse_video_detail(payload)
