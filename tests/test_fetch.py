import asyncio

import httpx
import pytest

from app.scraper.fetch import USER_AGENT, FetchError, fetch_html


class FakeResponse:
    def __init__(self, status_code=200, headers=None, text="<html><body>ok</body></html>"):
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}
        self.text = text


class FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.last_headers = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, headers=None):
        self.last_headers = headers
        if self._exc is not None:
            raise self._exc
        return self._response


def _patch_client(monkeypatch, **kwargs):
    fake = FakeAsyncClient(**kwargs)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake)
    return fake


def test_fetch_html_returns_body_on_success(monkeypatch):
    _patch_client(monkeypatch, response=FakeResponse(text="<html>hi</html>"))

    html = asyncio.run(fetch_html("https://example.com"))

    assert html == "<html>hi</html>"


def test_fetch_html_sends_a_user_agent_header(monkeypatch):
    fake = _patch_client(monkeypatch, response=FakeResponse())

    asyncio.run(fetch_html("https://example.com"))

    assert fake.last_headers["User-Agent"] == USER_AGENT


def test_fetch_html_raises_on_network_failure(monkeypatch):
    _patch_client(monkeypatch, exc=httpx.ConnectError("connection refused"))

    with pytest.raises(FetchError, match="Failed to reach"):
        asyncio.run(fetch_html("https://example.com"))


def test_fetch_html_raises_on_non_2xx_status(monkeypatch):
    _patch_client(monkeypatch, response=FakeResponse(status_code=404))

    with pytest.raises(FetchError, match="returned status 404"):
        asyncio.run(fetch_html("https://example.com"))


def test_fetch_html_raises_on_non_html_content_type(monkeypatch):
    _patch_client(monkeypatch, response=FakeResponse(headers={"content-type": "application/json"}))

    with pytest.raises(FetchError, match="did not return HTML content"):
        asyncio.run(fetch_html("https://example.com"))
