from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from seedr_tg.direct.renamer import FilenameRenamer
from seedr_tg.status.outcome import RequesterIdentity
from seedr_tg.telegram.media_rename import (
    MediaRenameOptions,
    TelegramMediaDescriptor,
    TelegramMediaRenameHandler,
)


def test_rename_parser_accepts_unquoted_multiword_explicit_name():
    options = TelegramMediaRenameHandler._parse_options(
        "/rename Small Soldiers 1998 REMASTERED 1080p BluRay.mkv"
    )

    assert options.explicit_name == "Small Soldiers 1998 REMASTERED 1080p BluRay.mkv"
    assert options.prefix is None
    assert options.substitutions == []


def test_rename_parser_accepts_multiword_rename_value_before_flags():
    options = TelegramMediaRenameHandler._parse_options(
        "/rename --rename Small Soldiers 1998.mkv --prefix [TAG]"
    )

    assert options.explicit_name == "Small Soldiers 1998.mkv"
    assert options.prefix == "[TAG]"


@pytest.mark.asyncio
async def test_rename_flow_passes_requester_user_settings_to_uploader(tmp_path):
    class _Repository:
        def __init__(self) -> None:
            self.user_ids: list[int] = []
            self.upload_settings = object()
            self.user_settings = object()

        async def get_upload_settings(self):
            return self.upload_settings

        async def get_user_settings(self, user_id: int):
            self.user_ids.append(user_id)
            return self.user_settings

    class _Uploader:
        def __init__(self) -> None:
            self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        async def upload_files(self, *args, **kwargs):
            self.calls.append((args, kwargs))

        def resolve_mtproto_chat_id(self, *, bot_chat_id: int, is_private_chat: bool) -> int:
            del bot_chat_id, is_private_chat
            raise AssertionError("MTProto fallback should not be used in this test")

        async def download_telegram_message_media(self, **kwargs):
            del kwargs
            raise AssertionError("MTProto fallback should not be used in this test")

    class _TelegramFile:
        async def download_to_drive(self, *, custom_path: str) -> None:
            Path(custom_path).write_bytes(b"payload")

    class _Bot:
        async def get_file(self, file_id: str):
            del file_id
            return _TelegramFile()

    class _Message:
        def __init__(self) -> None:
            self.message_id = 777
            self.reply_to_message = SimpleNamespace(
                chat=SimpleNamespace(id=123, type="private"),
                message_id=778,
            )
            self.replies: list[tuple[tuple[object, ...], dict[str, object]]] = []

        async def reply_text(self, *args, **kwargs) -> None:
            self.replies.append((args, kwargs))

    async def _noop_is_chat_allowed(chat_id: int) -> bool:
        del chat_id
        return True

    async def _noop_update_status(**kwargs) -> None:
        del kwargs

    async def _noop_ensure_not_canceled() -> None:
        return None

    uploader = _Uploader()
    repository = _Repository()
    handler = TelegramMediaRenameHandler(
        uploader=uploader,
        repository=repository,
        renamer=FilenameRenamer(max_filename_bytes=255),
        download_root=tmp_path,
        is_chat_allowed_callback=_noop_is_chat_allowed,
        bot_start_time=time.monotonic(),
    )

    message = _Message()
    temp_dir = tmp_path / "rename-test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_download_path = temp_dir / "payload.part"

    await handler._run_rename_flow(
        message=message,
        chat_id=123,
        requester=RequesterIdentity(user_id=42, username="u42", display_name="User 42"),
        started_at=time.monotonic(),
        selected_mode="rename",
        descriptor=TelegramMediaDescriptor(
            file_id="file-id",
            original_name="Original.Name.mkv",
            size_bytes=7,
        ),
        options=MediaRenameOptions(explicit_name="Renamed.Name"),
        context=SimpleNamespace(bot=_Bot()),
        temp_dir=temp_dir,
        temp_download_path=temp_download_path,
        speed_samples={},
        measure_speed=lambda _channel, _current_bytes: 0.0,
        render_transfer_detail=lambda **_kwargs: "",
        update_status=_noop_update_status,
        ensure_not_canceled=_noop_ensure_not_canceled,
    )

    assert repository.user_ids == [42]
    assert len(uploader.calls) == 1
    _, kwargs = uploader.calls[0]
    assert kwargs["upload_settings"] is repository.upload_settings
    assert kwargs["user_settings"] is repository.user_settings
