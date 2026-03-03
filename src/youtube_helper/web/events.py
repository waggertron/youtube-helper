from __future__ import annotations

import asyncio
import json


class EventBroadcaster:
    """In-memory pub/sub for SSE events."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    async def publish(self, event: dict) -> None:
        for queue in self._subscribers:
            await queue.put(event)

    async def subscribe(self):
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.remove(queue)

    def serialize(self, event: dict) -> str:
        return json.dumps(event)
