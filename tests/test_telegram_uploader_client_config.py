from __future__ import annotations

# pylint: disable=protected-access

from seedr_tg.telegram import uploader as uploader_module
from seedr_tg.telegram.uploader import TelegramUploader


class _StubRepository:
    async def get_telegram_user_session(self):  # pragma: no cover - not used in this test
        return None


def test_create_client_applies_max_concurrent_transmissions(monkeypatch):
    captured_kwargs: dict[str, object] = {}

    class DummyClient:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setattr(uploader_module, "Client", DummyClient)

    uploader = TelegramUploader(
        api_id=1,
        api_hash="hash",
        bot_token="123:token",
        target_chat_id=-100123,
        repository=_StubRepository(),
        max_concurrent_transmissions=6,
    )

    uploader._create_client("session-string", name="test-client", in_memory=True)

    assert captured_kwargs["max_concurrent_transmissions"] == 6
    assert captured_kwargs["session_string"] == "session-string"
