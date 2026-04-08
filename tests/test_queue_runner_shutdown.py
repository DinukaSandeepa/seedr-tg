from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from seedr_tg.worker.queue_runner import QueueRunner


@pytest.mark.asyncio
async def test_stop_cancels_active_job_tasks() -> None:
    runner = QueueRunner.__new__(QueueRunner)

    canceled = asyncio.Event()

    async def never_ending_job() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            canceled.set()
            raise

    object.__setattr__(runner, "_stop_event", asyncio.Event())
    object.__setattr__(runner, "_wake_event", asyncio.Event())
    object.__setattr__(runner, "_job_tasks", {1: asyncio.create_task(never_ending_job())})

    await asyncio.sleep(0)

    await runner.stop()

    assert canceled.is_set()
    assert runner._job_tasks == {}


@pytest.mark.asyncio
async def test_run_cleans_up_job_tasks_when_runner_task_is_cancelled() -> None:
    runner = QueueRunner.__new__(QueueRunner)

    canceled = asyncio.Event()

    async def never_ending_job() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            canceled.set()
            raise

    class _Repo:
        async def renumber_queue(self):
            return None

        async def claim_next_queued_job(self):
            return None

        async def get_next_job(self):
            return None

    async def _noop_recover() -> None:
        return None

    object.__setattr__(runner, "_repository", _Repo())
    object.__setattr__(runner, "_settings", SimpleNamespace(poll_interval_seconds=60.0))
    object.__setattr__(runner, "_stop_event", asyncio.Event())
    object.__setattr__(runner, "_wake_event", asyncio.Event())
    object.__setattr__(runner, "_queue_concurrency", 1)
    object.__setattr__(runner, "_job_tasks", {1: asyncio.create_task(never_ending_job())})
    object.__setattr__(runner, "_recover_unfinished_jobs", _noop_recover)
    object.__setattr__(runner, "_collect_finished_tasks", lambda: None)

    run_task = asyncio.create_task(runner.run())
    await asyncio.sleep(0)
    run_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await run_task

    assert canceled.is_set()
    assert runner._job_tasks == {}