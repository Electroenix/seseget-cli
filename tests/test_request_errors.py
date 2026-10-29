from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

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
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
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

    manager.sleeps = []

    async def no_sleep(seconds):
        manager.sleeps.append(seconds)

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


def test_retry_delay_is_exponential(monkeypatch):
    monkeypatch.setattr(requests_module.random, "uniform", lambda _low, _high: 0)

    assert requests_module._retry_delay(1) == 1.0
    assert requests_module._retry_delay(2) == 2.0
    assert requests_module._retry_delay(3) == 4.0
    assert requests_module._retry_delay(10) == requests_module.RETRY_MAX_DELAY


def test_retry_after_is_capped():
    assert requests_module._retry_delay(1, retry_after=120) == requests_module.RETRY_MAX_DELAY


@pytest.mark.asyncio
async def test_backoff_sleeps_between_retries(monkeypatch):
    manager = install_fake(
        monkeypatch,
        [FakeResponse(500), FakeResponse(500), FakeResponse(200)],
    )
    monkeypatch.setattr(requests_module.random, "uniform", lambda _low, _high: 0)

    response = await requests_module.async_request("GET", "https://example.test")

    assert response.status_code == 200
    assert manager.sleeps == [1.0, 2.0]


@pytest.mark.asyncio
async def test_retry_after_seconds_takes_precedence(monkeypatch):
    manager = install_fake(
        monkeypatch,
        [
            FakeResponse(429, headers={"Retry-After": "7"}),
            FakeResponse(200),
        ],
    )

    response = await requests_module.async_request("GET", "https://example.test")

    assert response.status_code == 200
    assert manager.sleeps == [7.0]


def test_retry_after_http_date_is_parsed():
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=10)
    response = FakeResponse(
        headers={"Retry-After": format_datetime(retry_at, usegmt=True)}
    )

    delay = requests_module._retry_after_seconds(response)

    assert delay is not None
    assert 8 <= delay <= 10


def test_invalid_retry_after_is_ignored():
    response = FakeResponse(headers={"Retry-After": "not-a-date"})

    assert requests_module._retry_after_seconds(response) is None
