import pytest

from seseget.request.errors import (
    RequestHTTPError,
    SiteAccessError,
    SiteParseError,
)
from seseget.request.fetcher import SSGBaseFetcher


class ParseFailure:
    async def _fetch_info(self, url, **kwargs):
        raise AttributeError("missing element")


class RequestFailure:
    async def _fetch_info(self, url, **kwargs):
        raise RequestHTTPError(
            "upstream 403",
            method="GET",
            url=url,
            attempts=1,
            status_code=403,
        )


class AccessFailure:
    async def _fetch_info(self, url, **kwargs):
        raise SiteAccessError("需要重新登录", site="test", url=url)


@pytest.mark.asyncio
async def test_parse_exception_wrapped_as_site_parse_error():
    with pytest.raises(SiteParseError) as exc_info:
        await SSGBaseFetcher._fetch_info_guarded(
            ParseFailure(), "https://example.test"
        )

    assert isinstance(exc_info.value.__cause__, AttributeError)
    assert exc_info.value.url == "https://example.test"
    assert "反爬" in str(exc_info.value)


@pytest.mark.asyncio
async def test_request_error_is_not_wrapped():
    with pytest.raises(RequestHTTPError):
        await SSGBaseFetcher._fetch_info_guarded(
            RequestFailure(), "https://example.test"
        )


@pytest.mark.asyncio
async def test_site_access_error_is_not_wrapped():
    with pytest.raises(SiteAccessError):
        await SSGBaseFetcher._fetch_info_guarded(
            AccessFailure(), "https://example.test"
        )
