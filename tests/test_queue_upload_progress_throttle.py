from __future__ import annotations

from types import SimpleNamespace

import pytest

from seedr_tg.worker.queue_runner import QueueRunner


@pytest.mark.asyncio
async def test_track_upload_progress_skips_transition_when_not_due():
    runner = QueueRunner.__new__(QueueRunner)

    transitions: list[dict[str, object]] = []
    sync_calls = 0
    cancellation_checks = 0

    async def fake_transition(job_id: int, **updates):
        del job_id
        transitions.append(updates)
        return SimpleNamespace(**updates)

    async def fake_sync(_job):
        nonlocal sync_calls
        sync_calls += 1

    async def fake_check(_job_id: int):
        nonlocal cancellation_checks
        cancellation_checks += 1

    object.__setattr__(runner, "_transition", fake_transition)
    object.__setattr__(runner, "_sync_admin_message_best_effort", fake_sync)
    object.__setattr__(runner, "_check_cancellation", fake_check)
    object.__setattr__(runner, "_compute_speed", lambda *_args, **_kwargs: 123.0)
    object.__setattr__(runner, "_should_sync_progress", lambda *_args, **_kwargs: False)

    await runner._track_upload_progress(
        job_id=7,
        completed_files=0,
        total_files=2,
        detail="Uploading",
        current_bytes=50,
        total_bytes=100,
    )

    assert transitions == []
    assert sync_calls == 0
    assert cancellation_checks == 1


@pytest.mark.asyncio
async def test_track_upload_progress_persists_on_file_boundary_even_if_not_due():
    runner = QueueRunner.__new__(QueueRunner)

    transitions: list[dict[str, object]] = []
    sync_calls = 0
    cancellation_checks = 0

    async def fake_transition(job_id: int, **updates):
        del job_id
        transitions.append(updates)
        return SimpleNamespace(**updates)

    async def fake_sync(_job):
        nonlocal sync_calls
        sync_calls += 1

    async def fake_check(_job_id: int):
        nonlocal cancellation_checks
        cancellation_checks += 1

    object.__setattr__(runner, "_transition", fake_transition)
    object.__setattr__(runner, "_sync_admin_message_best_effort", fake_sync)
    object.__setattr__(runner, "_check_cancellation", fake_check)
    object.__setattr__(runner, "_compute_speed", lambda *_args, **_kwargs: 321.0)
    object.__setattr__(runner, "_should_sync_progress", lambda *_args, **_kwargs: False)

    await runner._track_upload_progress(
        job_id=8,
        completed_files=1,
        total_files=2,
        detail="Uploaded part",
        current_bytes=100,
        total_bytes=100,
    )

    assert len(transitions) == 1
    assert transitions[0]["upload_speed_bps"] == 321.0
    assert sync_calls == 1
    assert cancellation_checks == 1