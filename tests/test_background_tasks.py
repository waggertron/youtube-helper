# tests/test_background_tasks.py
import asyncio
import pytest
from youtube_helper.web.tasks import BackgroundTasks


@pytest.fixture
def tasks():
    return BackgroundTasks()


def test_initial_status_is_none(tasks):
    assert tasks.get_status("sync") is None


@pytest.mark.asyncio
async def test_run_task_tracks_status(tasks):
    async def fake_job(update):
        update(progress=50, message="halfway")
        await asyncio.sleep(0.01)
        update(progress=100, message="done")

    task_id = tasks.start("sync", fake_job)
    assert task_id == "sync"

    # Let it finish
    await asyncio.sleep(0.1)

    status = tasks.get_status("sync")
    assert status["status"] == "completed"
    assert status["progress"] == 100


@pytest.mark.asyncio
async def test_run_task_captures_failure(tasks):
    async def failing_job(update):
        raise RuntimeError("boom")

    tasks.start("sync", failing_job)
    await asyncio.sleep(0.1)

    status = tasks.get_status("sync")
    assert status["status"] == "failed"
    assert "boom" in status["error"]


@pytest.mark.asyncio
async def test_cannot_start_duplicate_running_task(tasks):
    async def slow_job(update):
        await asyncio.sleep(10)

    tasks.start("sync", slow_job)
    with pytest.raises(RuntimeError, match="already running"):
        tasks.start("sync", slow_job)

    # Cleanup
    tasks._tasks["sync"]["asyncio_task"].cancel()
    try:
        await tasks._tasks["sync"]["asyncio_task"]
    except asyncio.CancelledError:
        pass
