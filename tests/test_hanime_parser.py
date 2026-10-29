from pathlib import Path

import pytest

from seseget.request.errors import SiteParseError
from seseget.sites.hanime import HanimeFetcher
from seseget.sites.parser import SiteParser

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "hanime"


def test_get_metadata_parses_fields():
    parser = SiteParser(
        (FIXTURE_DIR / "detail.html").read_text(encoding="utf-8"),
        site="hanime",
    )

    metadata = HanimeFetcher.get_metadata(parser)

    assert metadata.title == "测试标题"
    assert metadata.sub_title == "测试副标题"
    assert metadata.describe == "测试简介"
    assert metadata.author == "测试作者"
    assert metadata.series == "测试系列"
    assert metadata.public_time == "2026-09-30"
    assert metadata.year == "2026"
    assert metadata.tag_list == ["test_tag"]


def test_get_series_info_parses_playlist():
    parser = SiteParser(
        (FIXTURE_DIR / "detail.html").read_text(encoding="utf-8"),
        site="hanime",
    )

    series = HanimeFetcher.get_series_info(parser)

    assert series == [
        {
            "vid": "abc",
            "title": "第1话",
            "url": "https://example.test/watch?v=abc",
            "thumbnail": "https://example.test/thumb.jpg",
        }
    ]


def test_get_metadata_missing_title_reports_lookup():
    parser = SiteParser("<html></html>", site="hanime")

    with pytest.raises(SiteParseError) as exc_info:
        HanimeFetcher.get_metadata(parser)

    message = str(exc_info.value)
    assert "h3" in message
    assert "at=" in message


def test_get_series_info_missing_playlist_reports_lookup():
    parser = SiteParser("<html></html>", site="hanime")

    with pytest.raises(SiteParseError) as exc_info:
        HanimeFetcher.get_series_info(parser)

    assert "playlist-scroll" in str(exc_info.value)
