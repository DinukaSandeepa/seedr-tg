import pytest
from mongomock_motor import AsyncMongoMockClient

from seedr_tg.config import Settings
from seedr_tg.db.models import JobPhase
from seedr_tg.db.repository import JobRepository


@pytest.mark.asyncio
async def test_repository_enqueues_in_order() -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="token",
        TELEGRAM_API_ID=1,
        TELEGRAM_API_HASH="hash",
        TELEGRAM_SOURCE_CHAT_ID=1,
        TELEGRAM_TARGET_CHAT_ID=2,
        TELEGRAM_ADMIN_CHAT_ID=3,
        MONGODB_URI="mongodb://example.test",
        MONGODB_DATABASE="seedr_tg_test",
    )
    repository = JobRepository(
        settings.mongodb_uri,
        settings.mongodb_database,
        client=AsyncMongoMockClient(),
    )
    await repository.initialize()

    first = await repository.enqueue_job(
        magnet_link="magnet:?xt=urn:btih:1",
        source_chat_id=1,
        source_message_id=10,
        target_chat_id=2,
    )
    second = await repository.enqueue_job(
        magnet_link="magnet:?xt=urn:btih:2",
        source_chat_id=1,
        source_message_id=11,
        target_chat_id=2,
    )

    assert first.queue_position == 1
    assert second.queue_position == 2

    await repository.update_job(first.id, phase=JobPhase.COMPLETED)
    await repository.renumber_queue()
    jobs = await repository.list_jobs(include_final=False)
    assert jobs[0].id == second.id
    assert jobs[0].queue_position == 1
