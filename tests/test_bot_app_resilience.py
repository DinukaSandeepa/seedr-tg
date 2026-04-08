from __future__ import annotations

import pytest
from telegram.error import BadRequest, TimedOut

from seedr_tg.telegram.bot_app import TelegramBotApp


class _FakeMessage:
    def __init__(self, failures: list[BaseException] | None = None) -> None:
        self.failures = list(failures or [])
        self.calls = 0

    async def reply_text(self, **_kwargs):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return object()


class _FakeQuery:
    def __init__(self, failures: list[BaseException] | None = None) -> None:
        self.failures = list(failures or [])
        self.calls = 0

    async def edit_message_text(self, **_kwargs):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return object()


@pytest.mark.asyncio
async def test_safe_reply_text_retries_transient_timeout(monkeypatch) -> None:
    app = TelegramBotApp.__new__(TelegramBotApp)
    message = _FakeMessage([TimedOut("Timed out")])

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("seedr_tg.telegram.bot_app.asyncio.sleep", _no_sleep)

    sent = await app._safe_reply_text(message, text="hello", attempts=2)

    assert sent is True
    assert message.calls == 2


@pytest.mark.asyncio
async def test_safe_reply_text_returns_false_for_non_transient_bad_request() -> None:
    app = TelegramBotApp.__new__(TelegramBotApp)
    message = _FakeMessage([BadRequest("chat not found")])

    sent = await app._safe_reply_text(message, text="hello", attempts=2)

    assert sent is False
    assert message.calls == 1


@pytest.mark.asyncio
async def test_safe_edit_message_text_treats_not_modified_as_success() -> None:
    app = TelegramBotApp.__new__(TelegramBotApp)
    query = _FakeQuery([BadRequest("Message is not modified")])

    edited = await app._safe_edit_message_text(query, text="hello", attempts=2)

    assert edited is True
    assert query.calls == 1