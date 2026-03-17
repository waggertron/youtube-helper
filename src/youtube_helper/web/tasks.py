"""Lightweight background task manager. Replaces the queue system."""

import asyncio
from typing import Any, Callable, Awaitable


class BackgroundTasks:
    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}

    def start(
        self,
        name: str,
        coro_fn: Callable[[Callable], Awaitable[None]],
    ) -> str:
        existing = self._tasks.get(name)
        if existing and existing["status"] == "running":
            raise RuntimeError(f"Task '{name}' is already running")

        state = {
            "status": "running",
            "progress": 0,
            "message": "",
            "error": None,
            "asyncio_task": None,
        }

        def update(progress: int = 0, message: str = "", **extra):
            state["progress"] = progress
            state["message"] = message
            state.update(extra)

        async def wrapper():
            try:
                await coro_fn(update)
                state["status"] = "completed"
            except Exception as e:
                state["status"] = "failed"
                state["error"] = str(e)

        state["asyncio_task"] = asyncio.create_task(wrapper())
        self._tasks[name] = state
        return name

    def get_status(self, name: str) -> dict | None:
        state = self._tasks.get(name)
        if state is None:
            return None
        return {
            "status": state["status"],
            "progress": state["progress"],
            "message": state["message"],
            "error": state["error"],
        }
