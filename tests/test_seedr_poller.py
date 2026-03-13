from dataclasses import dataclass

import pytest

from seedr_tg.seedr.poller import SeedrPoller


@dataclass(slots=True)
class _FakeTorrent:
    progress: str
    progress_url: str | None = None
    folder: str | int | None = None


@dataclass(slots=True)
class _FakeResolved:
    title: str | None
    total_size_bytes: int | None
    torrent: _FakeTorrent | None
    folder: object | None
    has_files: bool


class _FakeSeedrService:
    def __init__(self, resolved: _FakeResolved) -> None:
        self._resolved = resolved

    async def resolve_torrent(self, torrent_id: int | None, known_folder_id: int | None = None):
        del torrent_id
        del known_folder_id
        return self._resolved

    async def get_torrent_progress(self, progress_url: str):
        del progress_url
        return None


@pytest.mark.asyncio
async def test_poller_completes_when_torrent_progress_reaches_100_without_progress_url() -> None:
    service = _FakeSeedrService(
        _FakeResolved(
            title="Test torrent",
            total_size_bytes=123,
            torrent=_FakeTorrent(progress="100", progress_url=None),
            folder=None,
            has_files=False,
        )
    )
    poller = SeedrPoller(service)

    snapshot = await poller.poll(1)

    assert snapshot.is_complete is True
    assert snapshot.progress_percent == 100.0


@pytest.mark.asyncio
async def test_poller_completes_when_root_files_exist_after_torrent_disappears() -> None:
    service = _FakeSeedrService(
        _FakeResolved(
            title="Recovered files",
            total_size_bytes=456,
            torrent=None,
            folder=None,
            has_files=True,
        )
    )
    poller = SeedrPoller(service)

    snapshot = await poller.poll(1)

    assert snapshot.is_complete is True
    assert snapshot.progress_percent == 100.0


@pytest.mark.asyncio
async def test_poller_uses_torrent_folder_id_when_folder_object_not_yet_visible() -> None:
    service = _FakeSeedrService(
        _FakeResolved(
            title="Folder pending",
            total_size_bytes=789,
            torrent=_FakeTorrent(progress="99.4", progress_url=None, folder="42"),
            folder=None,
            has_files=False,
        )
    )
    poller = SeedrPoller(service)

    snapshot = await poller.poll(1)

    assert snapshot.is_complete is True
    assert snapshot.seedr_folder_id == 42
