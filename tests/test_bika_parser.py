import pytest

from seseget.request.errors import SiteParseError
from seseget.sites.bika import parse_updated_at


def test_parse_updated_at():
    assert parse_updated_at("2026-09-13T11:22:05.073Z") == ("2026", "09", "13")


@pytest.mark.parametrize("value", [None, "", "not-a-date"])
def test_parse_updated_at_invalid(value):
    with pytest.raises(SiteParseError, match="updated_at"):
        parse_updated_at(value)
