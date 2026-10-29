import pytest

import seseget  # noqa: F401  # 触发站点发现和注册
from seseget.request.fetcher import FetcherRegistry

EXPECTED_SITES = {"hanime", "bilibili", "youtube", "twitter", "bika", "jmcomic", "wnacg"}


def test_all_sites_registered():
    assert EXPECTED_SITES.issubset(set(FetcherRegistry.list_sites()))


def test_unknown_site_raises_value_error():
    with pytest.raises(ValueError, match="未注册的站点"):
        FetcherRegistry.get_fetcher("not-a-site")
