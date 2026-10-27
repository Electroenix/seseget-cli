import pytest
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
from curl_cffi.requests.exceptions import Timeout as CurlTimeout

import seseget.request.requests as requests_module
from seseget.request.errors import (
    RequestConnectionError,
    RequestHTTPError,
    RequestTimeout,
)


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text
        self.closed = False

    def close(self):
        self.closed = True


class FakeSessionManager:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0
        self.last_kwargs = None

    async def request(self, method, url, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def default_network_config(monkeypatch):
    monkeypatch.setattr(
        requests_module,
        "config",
        {"network": {"proxy": "", "timeout": 10, "max_attempts": 3}},
    )


def install_fake(monkeypatch, results):
    manager = FakeSessionManager(results)
    monkeypatch.setattr(requests_module, "session_manager", manager)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(requests_module.asyncio, "sleep", no_sleep)
    return manager


@pytest.mark.asyncio
async def test_success_returns_response(monkeypatch):
    manager = install_fake(monkeypatch, [FakeResponse(200)])

    response = await requests_module.async_request("GET", "https://example.test")

    assert response.status_code == 200
    assert manager.calls == 1


@pytest.mark.asyncio
async def test_http_404_is_not_retried(monkeypatch):
    manager = install_fake(monkeypatch, [FakeResponse(404, "not found")])

    with pytest.raises(RequestHTTPError) as exc_info:
        await requests_module.async_request("GET", "https://example.test")

    assert manager.calls == 1
    assert exc_info.value.status_code == 404
    assert exc_info.value.attempts == 1
    assert exc_info.value.body_preview == "not found"


@pytest.mark.asyncio
async def test_http_500_retries_then_succeeds(monkeypatch):
    manager = install_fake(
        monkeypatch,
        [FakeResponse(500, "server error"), FakeResponse(200)],
    )

    response = await requests_module.async_request("GET", "https://example.test")

    assert response.status_code == 200
    assert manager.calls == 2


@pytest.mark.asyncio
async def test_http_500_raises_after_max_attempts(monkeypatch):
    manager = install_fake(
        monkeypatch,
        [FakeResponse(500) for _ in range(requests_module.REQUEST_MAX_ATTEMPTS)],
    )

    with pytest.raises(RequestHTTPError) as exc_info:
        await requests_module.async_request("GET", "https://example.test")

    assert manager.calls == requests_module.REQUEST_MAX_ATTEMPTS
    assert exc_info.value.attempts == requests_module.REQUEST_MAX_ATTEMPTS
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_http_429_retries(monkeypatch):
    manager = install_fake(monkeypatch, [FakeResponse(429), FakeResponse(200)])

    response = await requests_module.async_request("GET", "https://example.test")

    assert response.status_code == 200
    assert manager.calls == 2


@pytest.mark.asyncio
async def test_timeout_raises_after_max_attempts(monkeypatch):
    manager = install_fake(
        monkeypatch,
        [CurlTimeout("timed out") for _ in range(requests_module.REQUEST_MAX_ATTEMPTS)],
    )

    with pytest.raises(RequestTimeout) as exc_info:
        await requests_module.async_request("POST", "https://example.test")

    assert manager.calls == requests_module.REQUEST_MAX_ATTEMPTS
    assert exc_info.value.method == "POST"


@pytest.mark.asyncio
async def test_connection_error_raises(monkeypatch):
    manager = install_fake(
        monkeypatch,
        [CurlConnectionError("connection refused") for _ in range(requests_module.REQUEST_MAX_ATTEMPTS)],
    )

    with pytest.raises(RequestConnectionError) as exc_info:
        await requests_module.async_request("GET", "https://example.test")

    assert manager.calls == requests_module.REQUEST_MAX_ATTEMPTS
    assert exc_info.value.url == "https://example.test"


def test_configured_timeout_is_read():
    requests_module.config["network"]["timeout"] = 7

    assert requests_module._request_timeout() == 7


@pytest.mark.asyncio
async def test_configured_max_attempts_is_used(monkeypatch):
    manager = install_fake(
        monkeypatch,
        [FakeResponse(500), FakeResponse(500), FakeResponse(200)],
    )
    requests_module.config["network"]["max_attempts"] = 2

    with pytest.raises(RequestHTTPError) as exc_info:
        await requests_module.async_request("GET", "https://example.test")

    assert manager.calls == 2
    assert exc_info.value.attempts == 2


@pytest.mark.asyncio
async def test_max_attempts_one_disables_retry(monkeypatch):
    manager = install_fake(monkeypatch, [FakeResponse(500)])
    requests_module.config["network"]["max_attempts"] = 1

    with pytest.raises(RequestHTTPError):
        await requests_module.async_request("GET", "https://example.test")

    assert manager.calls == 1
