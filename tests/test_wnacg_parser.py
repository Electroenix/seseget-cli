from pathlib import Path

import pytest

from seseget.request.errors import SiteParseError
from seseget.sites.wnacg import parse_comic_info, parse_image_urls


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "wnacg"


def test_parse_image_urls_keeps_all_protocol_relative_urls():
    html = (FIXTURE_DIR / "photos.html").read_text(encoding="utf-8")

    urls = parse_image_urls(html)

    assert urls == [
        "https://cdn.example/1.jpg",
        "https://cdn.example/2.jpg",
    ]


def test_parse_comic_info_from_fixture():
    html = (FIXTURE_DIR / "comic.html").read_text(encoding="utf-8")

    comic = parse_comic_info(
        html,
        "https://example.test/123.html",
        "123",
        ["https://cdn.example/1.jpg"],
    )

    assert comic.title == "Test Comic"
    assert comic.author == "Test Author"
    assert comic.cover_url == "https://cdn.example/cover.jpg"
    assert comic.genres == ["tag1", "tag2", "同人"]
    assert comic.description == "A & B"
    assert comic.chapter_list[0].metadata.year == "2024"
    assert comic.chapter_list[0].metadata.month == "01"
    assert comic.chapter_list[0].metadata.day == "02"
    assert comic.chapter_list[0].image_urls == ["https://cdn.example/1.jpg"]


def test_missing_title_raises_site_parse_error():
    html = (FIXTURE_DIR / "comic.html").read_text(encoding="utf-8")
    html = html.replace("<h2>Test Comic</h2>", "")

    with pytest.raises(SiteParseError, match="h2"):
        parse_comic_info(html, "https://example.test/123.html", "123", [])


def test_missing_imglist_raises_site_parse_error():
    with pytest.raises(SiteParseError, match="image_list_match"):
        parse_image_urls("<html></html>", "https://example.test/123.html")
