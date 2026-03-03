import asyncio

import pytest

from youtube_helper.web.events import EventBroadcaster


class TestEventBroadcaster:
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        broadcaster = EventBroadcaster()
        received = []

        async def collect():
            async for event in broadcaster.subscribe():
                received.append(event)
                if len(received) >= 2:
                    break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.05)
        await broadcaster.publish({"type": "progress", "value": 50})
        await broadcaster.publish({"type": "progress", "value": 100})
        await task
        assert len(received) == 2
        assert received[0]["value"] == 50
        assert received[1]["value"] == 100

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        broadcaster = EventBroadcaster()
        results_a = []
        results_b = []

        async def collect(results):
            async for event in broadcaster.subscribe():
                results.append(event)
                if len(results) >= 1:
                    break

        task_a = asyncio.create_task(collect(results_a))
        task_b = asyncio.create_task(collect(results_b))
        await asyncio.sleep(0.05)
        await broadcaster.publish({"type": "test"})
        await task_a
        await task_b
        assert len(results_a) == 1
        assert len(results_b) == 1
