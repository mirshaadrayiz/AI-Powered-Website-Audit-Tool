import asyncio

import httpx
import pytest
from google.genai.errors import APIError
from pydantic import BaseModel

from app.llm.client import AIError, generate_structured


class DummySchema(BaseModel):
    value: int


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeModels:
    """Replays one action (a response or an exception) per call, in order."""

    def __init__(self, actions):
        self._actions = list(actions)
        self.call_count = 0

    async def generate_content(self, **kwargs):
        self.call_count += 1
        action = self._actions.pop(0)
        if isinstance(action, Exception):
            raise action
        return action


class FakeAio:
    def __init__(self, models):
        self.models = models


class FakeClient:
    def __init__(self, actions):
        self.aio = FakeAio(FakeModels(actions))


def _patch_client(monkeypatch, actions):
    fake = FakeClient(actions)
    monkeypatch.setattr("app.llm.client._client", lambda: fake)
    return fake


def _patch_no_sleep(monkeypatch):
    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr("app.llm.client.asyncio.sleep", fake_sleep)


def _patch_log_call(monkeypatch):
    calls = []
    monkeypatch.setattr("app.llm.client.log_call", lambda **kwargs: calls.append(kwargs))
    return calls


def test_generate_structured_returns_parsed_result_on_first_success(monkeypatch):
    fake = _patch_client(monkeypatch, [FakeResponse('{"value": 42}')])
    log_calls = _patch_log_call(monkeypatch)

    raw_text, parsed = asyncio.run(generate_structured("system prompt", "user prompt", DummySchema))

    assert raw_text == '{"value": 42}'
    assert parsed == DummySchema(value=42)
    assert fake.aio.models.call_count == 1
    assert len(log_calls) == 1
    assert log_calls[0]["attempt"] == 1


def test_generate_structured_retries_on_timeout_then_succeeds(monkeypatch):
    _patch_no_sleep(monkeypatch)
    fake = _patch_client(monkeypatch, [httpx.TimeoutException("slow"), FakeResponse('{"value": 7}')])
    _patch_log_call(monkeypatch)

    _, parsed = asyncio.run(generate_structured("s", "u", DummySchema))

    assert parsed.value == 7
    assert fake.aio.models.call_count == 2


def test_generate_structured_retries_on_schema_violating_output(monkeypatch):
    _patch_no_sleep(monkeypatch)
    fake = _patch_client(
        monkeypatch, [FakeResponse('{"wrong_field": 1}'), FakeResponse('{"value": 9}')]
    )
    _patch_log_call(monkeypatch)

    _, parsed = asyncio.run(generate_structured("s", "u", DummySchema))

    assert parsed.value == 9
    assert fake.aio.models.call_count == 2


def test_generate_structured_retries_on_retryable_5xx(monkeypatch):
    _patch_no_sleep(monkeypatch)
    server_error = APIError(503, {"error": {"message": "unavailable"}})
    fake = _patch_client(monkeypatch, [server_error, FakeResponse('{"value": 3}')])
    _patch_log_call(monkeypatch)

    _, parsed = asyncio.run(generate_structured("s", "u", DummySchema))

    assert parsed.value == 3
    assert fake.aio.models.call_count == 2


def test_generate_structured_does_not_retry_on_429(monkeypatch):
    _patch_no_sleep(monkeypatch)
    quota_error = APIError(429, {"error": {"message": "quota exceeded"}})
    fake = _patch_client(monkeypatch, [quota_error, FakeResponse('{"value": 1}')])
    log_calls = _patch_log_call(monkeypatch)

    with pytest.raises(AIError, match="after 1 attempt"):
        asyncio.run(generate_structured("s", "u", DummySchema))

    assert fake.aio.models.call_count == 1
    assert log_calls == []


def test_generate_structured_raises_after_max_attempts(monkeypatch):
    _patch_no_sleep(monkeypatch)
    fake = _patch_client(
        monkeypatch,
        [httpx.ConnectError("down"), httpx.ConnectError("down"), httpx.ConnectError("down")],
    )
    log_calls = _patch_log_call(monkeypatch)

    with pytest.raises(AIError, match="after 3 attempt"):
        asyncio.run(generate_structured("s", "u", DummySchema))

    assert fake.aio.models.call_count == 3
    assert log_calls == []
