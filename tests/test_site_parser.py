import pytest

from seseget.request.errors import SiteParseError
from seseget.sites.parser import SiteParser


def test_find_missing_element_reports_query_and_site():
    parser = SiteParser("<html><body></body></html>", site="demo")

    with pytest.raises(SiteParseError) as exc_info:
        parser.find(name="h2")

    message = str(exc_info.value)
    assert "at=" in message
    assert "site=demo" in message
    assert "find" in message
    assert "h2" in message


def test_nested_find_uses_node_context():
    parser = SiteParser(
        '<html><body><div class="box"><span class="title">x</span></div></body></html>',
        site="demo",
    )
    box = parser.find(name="div", attrs={"class": "box"})

    title = parser.find(node=box, name="span")

    assert title.get_text() == "x"


def test_find_all_missing_reports_operation():
    parser = SiteParser("<html></html>", site="demo")

    with pytest.raises(SiteParseError) as exc_info:
        parser.find_all(name="a")

    assert "find_all" in str(exc_info.value)
