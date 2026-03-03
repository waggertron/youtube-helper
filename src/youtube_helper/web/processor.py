# src/youtube_helper/web/processor.py
from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from youtube_helper.web.events import EventBroadcaster
from youtube_helper.web.queue import QueueManager


class QueueProcessor:
    def __init__(self, db_path: str, broadcaster: EventBroadcaster):
        self.db_path = db_path
        self.broadcaster = broadcaster
        self._handlers: dict[str, Callable] = {}
        self._running = False

    def register_handler(self, op_type: str, handler: Callable) -> None:
        self._handlers[op_type] = handler

    async def process_one(self) -> bool:
        qm = QueueManager(self.db_path)
        op = qm.next_pending()
        if not op:
            return False

        op_id = op["id"]
        op_type = op["type"]
        params = json.loads(op["params"])

        handler = self._handlers.get(op_type)
        if not handler:
            qm.update_operation(op_id, status="failed", error=f"Unknown operation: {op_type}")
            await self.broadcaster.publish({
                "type": "queue",
                "operation_id": op_id,
                "status": "failed",
                "error": f"Unknown operation: {op_type}",
            })
            return True

        qm.update_operation(op_id, status="active", progress=0.0, message="Starting...")
        await self.broadcaster.publish({
            "type": "queue",
            "operation_id": op_id,
            "status": "active",
        })

        async def progress_callback(progress: float, message: str = ""):
            qm.update_operation(op_id, progress=progress, message=message)
            await self.broadcaster.publish({
                "type": "queue",
                "operation_id": op_id,
                "progress": progress,
                "message": message,
            })

        try:
            await handler(params, progress_callback)
            qm.update_operation(op_id, status="completed", progress=100.0, message="Done")
            await self.broadcaster.publish({
                "type": "queue",
                "operation_id": op_id,
                "status": "completed",
            })
        except Exception as e:
            qm.update_operation(op_id, status="failed", error=str(e))
            await self.broadcaster.publish({
                "type": "queue",
                "operation_id": op_id,
                "status": "failed",
                "error": str(e),
            })

        return True

    async def run(self, poll_interval: float = 1.0) -> None:
        self._running = True
        while self._running:
            processed = await self.process_one()
            if not processed:
                await asyncio.sleep(poll_interval)

    def stop(self):
        self._running = False
