# Web Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full web dashboard (FastAPI + React + MUI) that wraps all existing CLI functionality with real-time progress via SSE, an operation queue, and explanatory UI text for every action.

**Architecture:** FastAPI backend in `src/youtube_helper/web/` wraps existing Python modules (no logic duplication). React + Vite + MUI frontend in `frontend/`. Long-running operations (sync, scrape, purge, export) execute via a sequential operation queue with SSE progress events. Production mode serves the built frontend as static files from FastAPI.

**Tech Stack:** FastAPI, uvicorn, sse-starlette, React 18, Vite, TypeScript, MUI v5, React Router v6, TanStack Query v5

**Testing:** TDD for ALL tasks (backend and frontend). Backend uses pytest + httpx. Frontend uses Vitest + React Testing Library. Write failing tests first, verify they fail, implement, verify they pass.

**Frontend testing dependencies (install in Task 10):**
- `vitest` — Test runner (Vite-native)
- `@testing-library/react` — Component testing
- `@testing-library/jest-dom` — DOM matchers
- `@testing-library/user-event` — User interaction simulation
- `jsdom` — DOM environment for tests
- `msw` (Mock Service Worker) — API mocking for integration tests

**Frontend test categories:**
- **Unit tests** — Pure functions, utilities, hooks (e.g., API client, useSSE)
- **Component tests** — Individual components render correctly with props (e.g., VideoTable, ConfirmDialog, ProgressBar)
- **Integration tests** — Full page tests with mocked API responses (e.g., Dashboard loads data, Search triggers queries, WatchLater filters work)

---

### Task 1: Backend Foundation — FastAPI App + Dependencies

**Files:**
- Modify: `pyproject.toml` (add fastapi, uvicorn, sse-starlette, httpx to deps)
- Create: `src/youtube_helper/web/__init__.py`
- Create: `src/youtube_helper/web/app.py`
- Create: `tests/test_web_app.py`

**Context:** This sets up the FastAPI application with CORS, a health endpoint, and the test infrastructure for all subsequent API route tasks. All future route modules will be registered as routers on this app.

**Step 1: Add web dependencies to pyproject.toml**

Add to the `dependencies` list in `pyproject.toml`:
```
"fastapi>=0.115",
"uvicorn[standard]>=0.30",
"sse-starlette>=2.0",
```

Add to `[project.optional-dependencies]` dev list:
```
"httpx>=0.27",
```

**Step 2: Write the failing test**

```python
# tests/test_web_app.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.web.app import create_app


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.db")
    from youtube_helper.db.migrations import run_migrations
    run_migrations(db_path)
    return create_app(db_path=db_path)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_includes_version(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert "version" in data
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_web_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'youtube_helper.web'`

**Step 4: Install new deps**

```bash
uv pip install -e ".[dev]"
```

Also add `pytest-asyncio` to dev deps in pyproject.toml:
```
"pytest-asyncio>=0.24",
```

And add to `[tool.pytest.ini_options]`:
```
asyncio_mode = "auto"
```

**Step 5: Write minimal implementation**

```python
# src/youtube_helper/web/__init__.py
```

```python
# src/youtube_helper/web/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app(db_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    from youtube_helper.config.settings import Settings

    settings = Settings()
    resolved_db_path = db_path or str(settings.db_path)

    app = FastAPI(title="YouTube Helper", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.db_path = resolved_db_path

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_web_app.py -v`
Expected: PASS

**Step 7: Run full test suite**

Run: `pytest -v`
Expected: All tests pass (65 existing + 2 new)

**Step 8: Lint**

Run: `ruff check src tests`
Expected: Clean

**Step 9: Commit**

```bash
git add pyproject.toml src/youtube_helper/web/ tests/test_web_app.py
git commit -m "feat: FastAPI app foundation with health endpoint"
```

---

### Task 2: Database Migration — Operation Queue Table

**Files:**
- Create: `migrations/002_operation_queue.sql`
- Create: `src/youtube_helper/web/queue.py`
- Create: `tests/test_queue.py`

**Context:** The operation queue stores pending/active/completed operations in SQLite. This task creates the table and a `QueueManager` class for CRUD operations on queue items. The actual background processing loop comes in Task 7.

**Step 1: Write the migration**

```sql
-- migrations/002_operation_queue.sql
CREATE TABLE operation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    params TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    progress REAL DEFAULT 0.0,
    message TEXT DEFAULT '',
    error TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX idx_queue_status ON operation_queue(status);
```

**Step 2: Write failing tests**

```python
# tests/test_queue.py
import json

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.queue import QueueManager


class TestQueueManager:
    def test_submit_operation(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        assert op_id == 1

    def test_list_operations(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        qm.submit("sync", {})
        qm.submit("scrape", {"headless": True})
        ops = qm.list_operations()
        assert len(ops) == 2
        assert ops[0]["type"] == "sync"
        assert ops[1]["type"] == "scrape"

    def test_get_operation(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {"verbose": True})
        op = qm.get_operation(op_id)
        assert op["type"] == "sync"
        assert json.loads(op["params"]) == {"verbose": True}
        assert op["status"] == "pending"

    def test_update_status(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="active", progress=50.0, message="Syncing...")
        op = qm.get_operation(op_id)
        assert op["status"] == "active"
        assert op["progress"] == 50.0

    def test_cancel_pending(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        result = qm.cancel_operation(op_id)
        assert result is True
        op = qm.get_operation(op_id)
        assert op["status"] == "cancelled"

    def test_cancel_active_fails(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="active")
        result = qm.cancel_operation(op_id)
        assert result is False

    def test_next_pending(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        qm.submit("sync", {})
        qm.submit("scrape", {})
        op = qm.next_pending()
        assert op["type"] == "sync"
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_queue.py -v`
Expected: FAIL — `ImportError`

**Step 4: Write minimal implementation**

```python
# src/youtube_helper/web/queue.py
from __future__ import annotations

import json

from youtube_helper.db.connection import get_connection


class QueueManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def submit(self, op_type: str, params: dict) -> int:
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            "INSERT INTO operation_queue (type, params) VALUES (?, ?)",
            (op_type, json.dumps(params)),
        )
        conn.commit()
        op_id = cursor.lastrowid
        conn.close()
        return op_id

    def list_operations(self) -> list[dict]:
        conn = get_connection(self.db_path)
        rows = conn.execute(
            "SELECT * FROM operation_queue ORDER BY id"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_operation(self, op_id: int) -> dict | None:
        conn = get_connection(self.db_path)
        row = conn.execute(
            "SELECT * FROM operation_queue WHERE id = ?", (op_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_operation(
        self,
        op_id: int,
        status: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> None:
        conn = get_connection(self.db_path)
        updates = []
        values = []
        if status is not None:
            updates.append("status = ?")
            values.append(status)
            if status == "active":
                updates.append("started_at = datetime('now')")
            elif status in ("completed", "failed"):
                updates.append("completed_at = datetime('now')")
        if progress is not None:
            updates.append("progress = ?")
            values.append(progress)
        if message is not None:
            updates.append("message = ?")
            values.append(message)
        if error is not None:
            updates.append("error = ?")
            values.append(error)
        values.append(op_id)
        conn.execute(
            f"UPDATE operation_queue SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        conn.commit()
        conn.close()

    def cancel_operation(self, op_id: int) -> bool:
        op = self.get_operation(op_id)
        if not op or op["status"] != "pending":
            return False
        self.update_operation(op_id, status="cancelled")
        return True

    def next_pending(self) -> dict | None:
        conn = get_connection(self.db_path)
        row = conn.execute(
            "SELECT * FROM operation_queue WHERE status = 'pending' ORDER BY id LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_queue.py -v`
Expected: PASS (7 tests)

**Step 6: Commit**

```bash
git add migrations/002_operation_queue.sql src/youtube_helper/web/queue.py tests/test_queue.py
git commit -m "feat: operation queue table and QueueManager"
```

---

### Task 3: SSE Event Broadcaster

**Files:**
- Create: `src/youtube_helper/web/events.py`
- Create: `src/youtube_helper/web/routes/__init__.py`
- Create: `src/youtube_helper/web/routes/events.py`
- Modify: `src/youtube_helper/web/app.py` (register events router)
- Create: `tests/test_events.py`

**Context:** The `EventBroadcaster` is an in-memory pub/sub that SSE clients subscribe to. Backend operations publish progress events. The SSE endpoint at `GET /api/events` streams these events to the frontend. This is the foundation for real-time progress on sync, scrape, export, and purge operations.

**Step 1: Write failing tests**

```python
# tests/test_events.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_events.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/youtube_helper/web/events.py
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
```

```python
# src/youtube_helper/web/routes/__init__.py
```

```python
# src/youtube_helper/web/routes/events.py
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
async def event_stream(request: Request):
    broadcaster = request.app.state.broadcaster

    async def generate():
        async for event in broadcaster.subscribe():
            if await request.is_disconnected():
                break
            yield {"data": broadcaster.serialize(event)}

    return EventSourceResponse(generate())
```

Update `src/youtube_helper/web/app.py` — add after the health endpoint:

```python
from youtube_helper.web.events import EventBroadcaster
from youtube_helper.web.routes.events import router as events_router

# Inside create_app, after app.state.db_path:
app.state.broadcaster = EventBroadcaster()
app.include_router(events_router)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_events.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/events.py src/youtube_helper/web/routes/ tests/test_events.py src/youtube_helper/web/app.py
git commit -m "feat: SSE event broadcaster and /api/events endpoint"
```

---

### Task 4: API Routes — Auth, Search, Sync

**Files:**
- Create: `src/youtube_helper/web/routes/auth.py`
- Create: `src/youtube_helper/web/routes/search.py`
- Create: `src/youtube_helper/web/routes/sync.py`
- Modify: `src/youtube_helper/web/app.py` (register routers)
- Create: `tests/test_web_routes_basic.py`

**Context:** These are simpler routes that wrap existing modules. Auth status checks if credentials exist. Search wraps `FuzzySearch.search_all()`. Sync submits a sync operation to the queue. The sync route does NOT run the sync directly — it submits to the operation queue (built in Task 7).

**Step 1: Write failing tests**

```python
# tests/test_web_routes_basic.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    return create_app(db_path=db_path)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAuthRoutes:
    @pytest.mark.asyncio
    async def test_auth_status(self, client):
        resp = await client.get("/api/auth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "authenticated" in data
        assert "has_client_secret" in data
        assert "has_token" in data


class TestSearchRoutes:
    @pytest.mark.asyncio
    async def test_search_empty_db(self, client):
        resp = await client.get("/api/search", params={"q": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_search_requires_query(self, client):
        resp = await client.get("/api/search")
        assert resp.status_code == 422


class TestSyncRoutes:
    @pytest.mark.asyncio
    async def test_sync_submits_to_queue(self, client):
        resp = await client.post("/api/sync")
        assert resp.status_code == 202
        data = resp.json()
        assert "operation_id" in data
        assert data["message"] == "Sync queued"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_routes_basic.py -v`
Expected: FAIL

**Step 3: Write implementations**

```python
# src/youtube_helper/web/routes/auth.py
from fastapi import APIRouter, Request

from youtube_helper.config.settings import Settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def auth_status(request: Request):
    settings = Settings()
    return {
        "authenticated": settings.token_path.exists(),
        "has_client_secret": settings.client_secret_path.exists(),
        "has_token": settings.token_path.exists(),
        "config_dir": str(settings.config_dir),
    }
```

```python
# src/youtube_helper/web/routes/search.py
from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=1),
    threshold: int = Query(60, ge=0, le=100),
):
    from youtube_helper.search.fuzzy import FuzzySearch

    searcher = FuzzySearch(request.app.state.db_path)
    results = searcher.search_all(q, threshold=threshold)
    return {"query": q, "results": results}
```

```python
# src/youtube_helper/web/routes/sync.py
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["sync"])


@router.post("/sync", status_code=202)
async def trigger_sync(request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("sync", {})
    return {"operation_id": op_id, "message": "Sync queued"}
```

Register all routers in `app.py`:
```python
from youtube_helper.web.routes.auth import router as auth_router
from youtube_helper.web.routes.search import router as search_router
from youtube_helper.web.routes.sync import router as sync_router

app.include_router(auth_router)
app.include_router(search_router)
app.include_router(sync_router)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_routes_basic.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/routes/ tests/test_web_routes_basic.py src/youtube_helper/web/app.py
git commit -m "feat: auth status, search, and sync API routes"
```

---

### Task 5: API Routes — Playlists CRUD + Reorder

**Files:**
- Create: `src/youtube_helper/web/routes/playlists.py`
- Modify: `src/youtube_helper/web/app.py` (register router)
- Create: `tests/test_web_playlists.py`

**Context:** Playlist routes read from the local SQLite database for list/show operations. Mutating operations (create, delete, add/remove videos, reorder) submit to the operation queue. The list and video-list endpoints return data directly from the DB since that's fast. This task tests the DB-read routes directly and verifies mutations submit queue items.

**Step 1: Write failing tests**

```python
# tests/test_web_playlists.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    """Seed DB with test playlists and videos."""
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title, privacy_status, video_count) "
        "VALUES ('PL1', 'Test Playlist', 'private', 2)"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V1', 'Video One', 'Channel A', 0.0)"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V2', 'Video Two', 'Channel B', 75.0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('PL1', 'V1', 0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('PL1', 'V2', 1)"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def app(seeded_db):
    return create_app(db_path=seeded_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestPlaylistRoutes:
    @pytest.mark.asyncio
    async def test_list_playlists(self, client):
        resp = await client.get("/api/playlists")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["playlists"]) == 1
        assert data["playlists"][0]["title"] == "Test Playlist"

    @pytest.mark.asyncio
    async def test_get_playlist_videos(self, client):
        resp = await client.get("/api/playlists/PL1/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["videos"]) == 2
        assert data["videos"][0]["title"] == "Video One"

    @pytest.mark.asyncio
    async def test_get_nonexistent_playlist(self, client):
        resp = await client.get("/api/playlists/NOPE/videos")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_playlist_queues(self, client):
        resp = await client.post(
            "/api/playlists",
            json={"title": "New Playlist", "privacy": "private"},
        )
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_delete_playlist_queues(self, client):
        resp = await client.delete("/api/playlists/PL1")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_add_video_queues(self, client):
        resp = await client.post(
            "/api/playlists/PL1/videos",
            json={"video_ids": ["V3"]},
        )
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_remove_video_queues(self, client):
        resp = await client.delete("/api/playlists/PL1/videos/V1")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_reorder_queues(self, client):
        resp = await client.put(
            "/api/playlists/PL1/reorder",
            json={"video_ids": ["V2", "V1"]},
        )
        assert resp.status_code == 202
        assert "operation_id" in resp.json()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_playlists.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/youtube_helper/web/routes/playlists.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from youtube_helper.db.connection import get_connection

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class CreatePlaylistRequest(BaseModel):
    title: str
    description: str = ""
    privacy: str = "private"


class AddVideosRequest(BaseModel):
    video_ids: list[str]


class ReorderRequest(BaseModel):
    video_ids: list[str]


@router.get("")
async def list_playlists(request: Request):
    conn = get_connection(request.app.state.db_path)
    rows = conn.execute(
        "SELECT * FROM playlists ORDER BY title"
    ).fetchall()
    conn.close()
    return {"playlists": [dict(r) for r in rows]}


@router.get("/{playlist_id}/videos")
async def get_playlist_videos(playlist_id: str, request: Request):
    conn = get_connection(request.app.state.db_path)
    playlist = conn.execute(
        "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
    ).fetchone()
    if not playlist:
        conn.close()
        raise HTTPException(status_code=404, detail="Playlist not found")
    rows = conn.execute(
        """SELECT v.*, pv.position FROM videos v
           JOIN playlist_videos pv ON v.id = pv.video_id
           WHERE pv.playlist_id = ?
           ORDER BY pv.position""",
        (playlist_id,),
    ).fetchall()
    conn.close()
    return {"playlist": dict(playlist), "videos": [dict(r) for r in rows]}


@router.post("", status_code=202)
async def create_playlist(body: CreatePlaylistRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("create_playlist", body.model_dump())
    return {"operation_id": op_id, "message": "Create playlist queued"}


@router.delete("/{playlist_id}", status_code=202)
async def delete_playlist(playlist_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("delete_playlist", {"playlist_id": playlist_id})
    return {"operation_id": op_id, "message": "Delete playlist queued"}


@router.post("/{playlist_id}/videos", status_code=202)
async def add_videos(playlist_id: str, body: AddVideosRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit(
        "add_videos", {"playlist_id": playlist_id, "video_ids": body.video_ids}
    )
    return {"operation_id": op_id, "message": "Add videos queued"}


@router.delete("/{playlist_id}/videos/{video_id}", status_code=202)
async def remove_video(playlist_id: str, video_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit(
        "remove_video", {"playlist_id": playlist_id, "video_id": video_id}
    )
    return {"operation_id": op_id, "message": "Remove video queued"}


@router.put("/{playlist_id}/reorder", status_code=202)
async def reorder_playlist(playlist_id: str, body: ReorderRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit(
        "reorder_playlist", {"playlist_id": playlist_id, "video_ids": body.video_ids}
    )
    return {"operation_id": op_id, "message": "Reorder queued"}
```

Register in `app.py`:
```python
from youtube_helper.web.routes.playlists import router as playlists_router
app.include_router(playlists_router)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_playlists.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/routes/playlists.py tests/test_web_playlists.py src/youtube_helper/web/app.py
git commit -m "feat: playlist CRUD and reorder API routes"
```

---

### Task 6: API Routes — Videos (Like/Unlike) + Watch Later

**Files:**
- Create: `src/youtube_helper/web/routes/videos.py`
- Create: `src/youtube_helper/web/routes/watch_later.py`
- Modify: `src/youtube_helper/web/app.py` (register routers)
- Create: `tests/test_web_videos.py`
- Create: `tests/test_web_watch_later.py`

**Context:** Video routes handle like/unlike (queued) and listing liked videos (DB read). Watch Later routes read from the DB for list/watched/unwatched, and submit scrape/export/purge/prune to the queue.

**Step 1: Write failing tests for video routes**

```python
# tests/test_web_videos.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO videos (id, title, channel_name) VALUES ('V1', 'Video One', 'Ch A')"
    )
    conn.execute(
        "INSERT INTO liked_videos (video_id, liked_at) VALUES ('V1', datetime('now'))"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def app(seeded_db):
    return create_app(db_path=seeded_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestVideoRoutes:
    @pytest.mark.asyncio
    async def test_list_liked(self, client):
        resp = await client.get("/api/videos/liked")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["videos"]) == 1

    @pytest.mark.asyncio
    async def test_like_video_queues(self, client):
        resp = await client.post("/api/videos/V1/like")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_unlike_video_queues(self, client):
        resp = await client.delete("/api/videos/V1/like")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()
```

```python
# tests/test_web_watch_later.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title, source) VALUES ('WL', 'Watch Later', 'browser')"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V1', 'Watched Video', 'Ch A', 80.0)"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V2', 'Unwatched Video', 'Ch B', 10.0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) VALUES ('WL', 'V1', 0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) VALUES ('WL', 'V2', 1)"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def app(seeded_db):
    return create_app(db_path=seeded_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestWatchLaterRoutes:
    @pytest.mark.asyncio
    async def test_list_all(self, client):
        resp = await client.get("/api/watch-later")
        assert resp.status_code == 200
        assert len(resp.json()["videos"]) == 2

    @pytest.mark.asyncio
    async def test_watched(self, client):
        resp = await client.get("/api/watch-later/watched", params={"threshold": 50})
        assert resp.status_code == 200
        videos = resp.json()["videos"]
        assert len(videos) == 1
        assert videos[0]["title"] == "Watched Video"

    @pytest.mark.asyncio
    async def test_unwatched(self, client):
        resp = await client.get("/api/watch-later/unwatched", params={"threshold": 50})
        assert resp.status_code == 200
        videos = resp.json()["videos"]
        assert len(videos) == 1
        assert videos[0]["title"] == "Unwatched Video"

    @pytest.mark.asyncio
    async def test_scrape_queues(self, client):
        resp = await client.post("/api/watch-later/scrape")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_export_queues(self, client):
        resp = await client.post(
            "/api/watch-later/export",
            json={"target": "spacepope videos", "threshold": 50},
        )
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_purge_queues(self, client):
        resp = await client.post(
            "/api/watch-later/purge", json={"threshold": 50}
        )
        assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_prune_exports_queues(self, client):
        resp = await client.post("/api/watch-later/prune-exports")
        assert resp.status_code == 202
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_web_videos.py tests/test_web_watch_later.py -v`
Expected: FAIL

**Step 3: Write implementations**

```python
# src/youtube_helper/web/routes/videos.py
from fastapi import APIRouter, Request

from youtube_helper.db.connection import get_connection

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("/liked")
async def list_liked(request: Request):
    conn = get_connection(request.app.state.db_path)
    rows = conn.execute(
        """SELECT v.*, lv.liked_at FROM videos v
           JOIN liked_videos lv ON v.id = lv.video_id
           ORDER BY lv.liked_at DESC"""
    ).fetchall()
    conn.close()
    return {"videos": [dict(r) for r in rows]}


@router.post("/{video_id}/like", status_code=202)
async def like_video(video_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("like_video", {"video_id": video_id})
    return {"operation_id": op_id, "message": "Like queued"}


@router.delete("/{video_id}/like", status_code=202)
async def unlike_video(video_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("unlike_video", {"video_id": video_id})
    return {"operation_id": op_id, "message": "Unlike queued"}
```

```python
# src/youtube_helper/web/routes/watch_later.py
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from youtube_helper.db.connection import get_connection

router = APIRouter(prefix="/api/watch-later", tags=["watch-later"])


class ExportRequest(BaseModel):
    target: str = "spacepope videos"
    threshold: float = 50.0


class PurgeRequest(BaseModel):
    threshold: float = 50.0
    headless: bool = False


@router.get("")
async def list_watch_later(request: Request):
    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(request.app.state.db_path)
    videos = manager.export_playlist_data("WL")
    return {"videos": videos}


@router.get("/watched")
async def watched_videos(
    request: Request, threshold: float = Query(50.0, ge=0, le=100)
):
    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(request.app.state.db_path)
    videos = manager.get_watched_videos(threshold=threshold)
    return {"videos": videos, "threshold": threshold}


@router.get("/unwatched")
async def unwatched_videos(
    request: Request, threshold: float = Query(50.0, ge=0, le=100)
):
    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(request.app.state.db_path)
    videos = manager.get_unwatched_videos(threshold=threshold)
    return {"videos": videos, "threshold": threshold}


@router.post("/scrape", status_code=202)
async def scrape_watch_later(request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("scrape_watch_later", {})
    return {"operation_id": op_id, "message": "Scrape queued"}


@router.post("/export", status_code=202)
async def export_watch_later(body: ExportRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("export_watch_later", body.model_dump())
    return {"operation_id": op_id, "message": "Export queued"}


@router.post("/purge", status_code=202)
async def purge_watch_later(body: PurgeRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("purge_watch_later", body.model_dump())
    return {"operation_id": op_id, "message": "Purge queued"}


@router.post("/prune-exports", status_code=202)
async def prune_exports(request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("prune_exports", {})
    return {"operation_id": op_id, "message": "Prune queued"}
```

Register both routers in `app.py`.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_web_videos.py tests/test_web_watch_later.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/routes/videos.py src/youtube_helper/web/routes/watch_later.py tests/test_web_videos.py tests/test_web_watch_later.py src/youtube_helper/web/app.py
git commit -m "feat: video like/unlike and watch later API routes"
```

---

### Task 7: Operation Queue — Routes + Background Processor

**Files:**
- Create: `src/youtube_helper/web/routes/queue.py`
- Create: `src/youtube_helper/web/processor.py`
- Modify: `src/youtube_helper/web/app.py` (register router, start processor on startup)
- Create: `tests/test_web_queue_routes.py`
- Create: `tests/test_processor.py`

**Context:** This is the core of the queue system. The `QueueProcessor` is an asyncio background task that polls for pending operations, executes them one at a time, and publishes progress events via the `EventBroadcaster`. The queue routes let the frontend list, cancel, retry, and skip operations. The processor dispatches to handler functions based on operation type (sync, scrape, export, etc.).

**Step 1: Write failing tests for queue routes**

```python
# tests/test_web_queue_routes.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app
from youtube_helper.web.queue import QueueManager


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def app(db_path):
    return create_app(db_path=db_path)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestQueueRoutes:
    @pytest.mark.asyncio
    async def test_list_queue_empty(self, client):
        resp = await client.get("/api/queue")
        assert resp.status_code == 200
        assert resp.json()["operations"] == []

    @pytest.mark.asyncio
    async def test_list_queue_with_items(self, client, db_path):
        qm = QueueManager(db_path)
        qm.submit("sync", {})
        resp = await client.get("/api/queue")
        assert len(resp.json()["operations"]) == 1

    @pytest.mark.asyncio
    async def test_cancel_pending(self, client, db_path):
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        resp = await client.delete(f"/api/queue/{op_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_retry_failed(self, client, db_path):
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="failed", error="Network error")
        resp = await client.post(f"/api/queue/{op_id}/retry")
        assert resp.status_code == 200
        op = qm.get_operation(op_id)
        assert op["status"] == "pending"

    @pytest.mark.asyncio
    async def test_skip_failed(self, client, db_path):
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="failed")
        resp = await client.post(f"/api/queue/{op_id}/skip")
        assert resp.status_code == 200
        op = qm.get_operation(op_id)
        assert op["status"] == "skipped"
```

**Step 2: Write failing tests for processor**

```python
# tests/test_processor.py
import pytest

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.events import EventBroadcaster
from youtube_helper.web.processor import QueueProcessor
from youtube_helper.web.queue import QueueManager


class TestQueueProcessor:
    @pytest.mark.asyncio
    async def test_processes_pending_operation(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        broadcaster = EventBroadcaster()

        op_id = qm.submit("test_noop", {})
        processor = QueueProcessor(db_path, broadcaster)
        processor.register_handler("test_noop", self._noop_handler)
        await processor.process_one()

        op = qm.get_operation(op_id)
        assert op["status"] == "completed"

    @pytest.mark.asyncio
    async def test_handles_failure(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        broadcaster = EventBroadcaster()

        op_id = qm.submit("test_fail", {})
        processor = QueueProcessor(db_path, broadcaster)
        processor.register_handler("test_fail", self._fail_handler)
        await processor.process_one()

        op = qm.get_operation(op_id)
        assert op["status"] == "failed"
        assert "boom" in op["error"]

    @staticmethod
    async def _noop_handler(params, progress_callback):
        await progress_callback(100.0, "Done")

    @staticmethod
    async def _fail_handler(params, progress_callback):
        raise RuntimeError("boom")
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_web_queue_routes.py tests/test_processor.py -v`
Expected: FAIL

**Step 4: Write implementations**

```python
# src/youtube_helper/web/routes/queue.py
from fastapi import APIRouter, HTTPException, Request

from youtube_helper.web.queue import QueueManager

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("")
async def list_queue(request: Request):
    qm = QueueManager(request.app.state.db_path)
    return {"operations": qm.list_operations()}


@router.delete("/{op_id}")
async def cancel_operation(op_id: int, request: Request):
    qm = QueueManager(request.app.state.db_path)
    if not qm.cancel_operation(op_id):
        raise HTTPException(400, "Can only cancel pending operations")
    return {"message": "Operation cancelled"}


@router.post("/{op_id}/retry")
async def retry_operation(op_id: int, request: Request):
    qm = QueueManager(request.app.state.db_path)
    op = qm.get_operation(op_id)
    if not op or op["status"] != "failed":
        raise HTTPException(400, "Can only retry failed operations")
    qm.update_operation(op_id, status="pending", progress=0.0, error="", message="")
    return {"message": "Operation requeued"}


@router.post("/{op_id}/skip")
async def skip_operation(op_id: int, request: Request):
    qm = QueueManager(request.app.state.db_path)
    op = qm.get_operation(op_id)
    if not op or op["status"] != "failed":
        raise HTTPException(400, "Can only skip failed operations")
    qm.update_operation(op_id, status="skipped")
    return {"message": "Operation skipped"}
```

```python
# src/youtube_helper/web/processor.py
from __future__ import annotations

import asyncio
import json
import traceback
from typing import Callable

from youtube_helper.web.events import EventBroadcaster
from youtube_helper.web.queue import QueueManager


class QueueProcessor:
    """Background processor that executes queued operations one at a time."""

    def __init__(self, db_path: str, broadcaster: EventBroadcaster):
        self.db_path = db_path
        self.broadcaster = broadcaster
        self._handlers: dict[str, Callable] = {}
        self._running = False

    def register_handler(self, op_type: str, handler: Callable) -> None:
        self._handlers[op_type] = handler

    async def process_one(self) -> bool:
        """Process the next pending operation. Returns True if one was processed."""
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
                "type": "queue", "operation_id": op_id, "status": "failed",
                "error": f"Unknown operation: {op_type}",
            })
            return True

        qm.update_operation(op_id, status="active", progress=0.0, message="Starting...")
        await self.broadcaster.publish({
            "type": "queue", "operation_id": op_id, "status": "active",
        })

        async def progress_callback(progress: float, message: str = ""):
            qm.update_operation(op_id, progress=progress, message=message)
            await self.broadcaster.publish({
                "type": "queue", "operation_id": op_id,
                "progress": progress, "message": message,
            })

        try:
            await handler(params, progress_callback)
            qm.update_operation(
                op_id, status="completed", progress=100.0, message="Done"
            )
            await self.broadcaster.publish({
                "type": "queue", "operation_id": op_id, "status": "completed",
            })
        except Exception as e:
            qm.update_operation(op_id, status="failed", error=str(e))
            await self.broadcaster.publish({
                "type": "queue", "operation_id": op_id, "status": "failed",
                "error": str(e),
            })

        return True

    async def run(self, poll_interval: float = 1.0) -> None:
        """Run the processor loop. Call this as a background task."""
        self._running = True
        while self._running:
            processed = await self.process_one()
            if not processed:
                await asyncio.sleep(poll_interval)

    def stop(self):
        self._running = False
```

Register queue router and start processor in `app.py`. Add a lifespan handler:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start queue processor
    from youtube_helper.web.processor import QueueProcessor
    processor = QueueProcessor(app.state.db_path, app.state.broadcaster)
    # Register operation handlers here (Task 7 continued — handlers added as they're built)
    app.state.processor = processor
    task = asyncio.create_task(processor.run())
    yield
    processor.stop()
    task.cancel()
```

Pass `lifespan=lifespan` to `FastAPI()` constructor.

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_web_queue_routes.py tests/test_processor.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/youtube_helper/web/routes/queue.py src/youtube_helper/web/processor.py tests/test_web_queue_routes.py tests/test_processor.py src/youtube_helper/web/app.py
git commit -m "feat: operation queue routes and background processor"
```

---

### Task 8: Operation Handlers — Wire Real Operations to Queue

**Files:**
- Create: `src/youtube_helper/web/handlers.py`
- Modify: `src/youtube_helper/web/app.py` (register handlers)
- Create: `tests/test_handlers.py`

**Context:** This task creates the handler functions that the `QueueProcessor` calls for each operation type. Each handler wraps the existing Python modules (SyncEngine, WatchLaterManager, PlaylistClient, etc.) and reports progress via the callback. Handlers that need YouTube API auth get it via `get_authenticated_service()`. Playwright-based handlers (scrape, purge) run async.

**Step 1: Write failing tests**

Test a handler that doesn't need YouTube API auth — we can test the scrape handler with a mock.

```python
# tests/test_handlers.py
import pytest

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.handlers import register_all_handlers
from youtube_helper.web.processor import QueueProcessor
from youtube_helper.web.events import EventBroadcaster


class TestHandlerRegistration:
    def test_all_handlers_registered(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        broadcaster = EventBroadcaster()
        processor = QueueProcessor(db_path, broadcaster)
        register_all_handlers(processor)
        expected = [
            "sync", "scrape_watch_later", "export_watch_later",
            "purge_watch_later", "prune_exports",
            "create_playlist", "delete_playlist",
            "add_videos", "remove_video", "reorder_playlist",
            "like_video", "unlike_video",
        ]
        for op_type in expected:
            assert op_type in processor._handlers, f"Missing handler: {op_type}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_handlers.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/youtube_helper/web/handlers.py
"""Operation handlers for the queue processor.

Each handler is an async function with signature:
    async def handler(params: dict, progress: Callable) -> None
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from youtube_helper.web.processor import QueueProcessor


def register_all_handlers(processor: QueueProcessor) -> None:
    """Register all operation handlers on the processor."""
    processor.register_handler("sync", handle_sync)
    processor.register_handler("scrape_watch_later", handle_scrape)
    processor.register_handler("export_watch_later", handle_export)
    processor.register_handler("purge_watch_later", handle_purge)
    processor.register_handler("prune_exports", handle_prune_exports)
    processor.register_handler("create_playlist", handle_create_playlist)
    processor.register_handler("delete_playlist", handle_delete_playlist)
    processor.register_handler("add_videos", handle_add_videos)
    processor.register_handler("remove_video", handle_remove_video)
    processor.register_handler("reorder_playlist", handle_reorder)
    processor.register_handler("like_video", handle_like)
    processor.register_handler("unlike_video", handle_unlike)


def _get_youtube_client(db_path: str):
    """Get authenticated YouTube API service and PlaylistClient."""
    from youtube_helper.api.auth import get_authenticated_service
    from youtube_helper.api.playlists import PlaylistClient
    from youtube_helper.config.settings import Settings

    settings = Settings()
    youtube = get_authenticated_service(settings)
    return youtube, PlaylistClient(youtube)


async def handle_sync(params, progress):
    from youtube_helper.config.settings import Settings
    from youtube_helper.sync.engine import SyncEngine

    settings = Settings()
    db_path = str(settings.db_path)
    await progress(10.0, "Connecting to YouTube...")
    _, client = _get_youtube_client(db_path)
    await progress(20.0, "Syncing playlists...")
    engine = SyncEngine(db_path, client)
    stats = engine.sync_all()
    await progress(100.0, f"Synced {stats['playlists']} playlists, {stats['videos']} videos")


async def handle_scrape(params, progress):
    from youtube_helper.browser.watch_later import scrape_watch_later
    from youtube_helper.config.settings import Settings
    from youtube_helper.watch_later.manager import WatchLaterManager

    settings = Settings()
    await progress(10.0, "Launching Chrome...")
    videos = await scrape_watch_later(headless=params.get("headless", False))
    await progress(80.0, f"Scraped {len(videos)} videos, saving...")
    manager = WatchLaterManager(str(settings.db_path))
    saved = manager.save_scraped_videos(videos)
    await progress(100.0, f"Saved {saved} videos")


async def handle_export(params, progress):
    from datetime import datetime

    from youtube_helper.config.settings import Settings
    from youtube_helper.watch_later.manager import WatchLaterManager

    settings = Settings()
    db_path = str(settings.db_path)
    threshold = params.get("threshold", 50.0)
    target = params.get("target", "spacepope videos")

    manager = WatchLaterManager(db_path)
    all_videos = manager.export_playlist_data("WL")
    watched = manager.get_watched_videos(threshold=threshold)
    unwatched = manager.get_unwatched_videos(threshold=threshold)

    if not all_videos:
        await progress(100.0, "No videos found in Watch Later")
        return

    await progress(10.0, "Connecting to YouTube...")
    youtube, client = _get_youtube_client(db_path)
    date_str = datetime.now().strftime("%Y-%m-%d")

    await progress(20.0, f"Creating 'Watch Later Export {date_str}'...")
    export_pl = client.create_playlist(
        f"Watch Later Export {date_str}",
        description=f"Exported from Watch Later on {date_str}",
        privacy="private",
    )
    for i, v in enumerate(all_videos):
        vid = v.get("id") or v.get("video_id")
        try:
            client.add_to_playlist(export_pl["id"], vid)
        except Exception:
            pass
        await progress(20 + (i / len(all_videos)) * 20, f"Adding to export ({i+1}/{len(all_videos)})")

    await progress(45.0, "Updating Watch Later Archive...")
    # Find or create archive
    playlists = client.list_playlists()
    archive_id = None
    for pl in playlists:
        if pl["snippet"]["title"] == "Watch Later Archive":
            archive_id = pl["id"]
            break
    if not archive_id:
        archive_pl = client.create_playlist("Watch Later Archive", privacy="private")
        archive_id = archive_pl["id"]

    for i, v in enumerate(all_videos):
        vid = v.get("id") or v.get("video_id")
        try:
            client.add_to_playlist(archive_id, vid)
        except Exception:
            pass
        await progress(45 + (i / len(all_videos)) * 20, f"Archiving ({i+1}/{len(all_videos)})")

    await progress(70.0, f"Copying unwatched to '{target}'...")
    target_id = None
    for pl in playlists:
        if pl["snippet"]["title"] == target:
            target_id = pl["id"]
            break
    if not target_id:
        target_pl = client.create_playlist(target, privacy="private")
        target_id = target_pl["id"]

    for i, v in enumerate(unwatched):
        vid = v.get("id") or v.get("video_id")
        try:
            client.add_to_playlist(target_id, vid)
        except Exception:
            pass
        if unwatched:
            await progress(
                70 + (i / len(unwatched)) * 20,
                f"Copying unwatched ({i+1}/{len(unwatched)})",
            )

    await progress(92.0, "Removing watched from local DB...")
    watched_ids = [v["id"] for v in watched]
    manager.remove_videos_from_db("WL", watched_ids)
    await progress(100.0, f"Export complete: {len(all_videos)} exported, {len(watched)} removed")


async def handle_purge(params, progress):
    from youtube_helper.config.settings import Settings
    from youtube_helper.watch_later.manager import WatchLaterManager

    settings = Settings()
    threshold = params.get("threshold", 50.0)
    headless = params.get("headless", False)
    manager = WatchLaterManager(str(settings.db_path))
    watched = manager.get_watched_videos(threshold=threshold)

    if not watched:
        await progress(100.0, "No watched videos to purge")
        return

    await progress(10.0, f"Launching Chrome to remove {len(watched)} videos...")

    # Import and run the purge browser automation
    import re

    from playwright.async_api import async_playwright

    from youtube_helper.browser.watch_later import find_chrome_profile_path

    chrome_path = find_chrome_profile_path()
    video_ids = {v["id"] for v in watched}

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_path, channel="chrome", headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(
            "https://www.youtube.com/playlist?list=WL", wait_until="networkidle"
        )
        await page.wait_for_selector("ytd-playlist-video-renderer", timeout=15000)

        for _ in range(50):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(500)

        removed = 0
        renderers = await page.query_selector_all("ytd-playlist-video-renderer")

        for renderer in renderers:
            link = await renderer.query_selector("a#thumbnail")
            href = await link.get_attribute("href") if link else ""
            match = re.search(r"v=([^&]+)", href or "")
            if not match:
                continue
            vid = match.group(1)

            if vid in video_ids:
                menu_btn = await renderer.query_selector(
                    "yt-icon-button#button, button[aria-label='Action menu']"
                )
                if menu_btn:
                    await menu_btn.click()
                    await page.wait_for_timeout(300)
                    remove_btn = await page.query_selector(
                        "tp-yt-paper-listbox ytd-menu-service-item-renderer:has-text('Remove from')"
                    )
                    if not remove_btn:
                        remove_btn = await page.query_selector(
                            "ytd-menu-service-item-renderer:has-text('Remove')"
                        )
                    if remove_btn:
                        await remove_btn.click()
                        await page.wait_for_timeout(500)
                        removed += 1
                        await progress(
                            10 + (removed / len(video_ids)) * 85,
                            f"Removed {removed}/{len(video_ids)}",
                        )

        await ctx.close()

    manager.remove_videos_from_db("WL", [v["id"] for v in watched])
    await progress(100.0, f"Purged {removed} videos")


async def handle_prune_exports(params, progress):
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    db_path = str(settings.db_path)
    await progress(10.0, "Connecting to YouTube...")
    _, client = _get_youtube_client(db_path)

    playlists = client.list_playlists()
    exports = [p for p in playlists if p["snippet"]["title"].startswith("Watch Later Export")]

    if not exports:
        await progress(100.0, "No export playlists found")
        return

    total_pruned = 0
    for i, pl in enumerate(exports):
        items = client.list_playlist_items(pl["id"])
        for item in items:
            vid_id = item["snippet"]["resourceId"]["videoId"]
            conn = get_connection(db_path)
            video = conn.execute(
                "SELECT watch_progress FROM videos WHERE id = ?", (vid_id,)
            ).fetchone()
            conn.close()
            if video and video["watch_progress"] >= 50.0:
                client.remove_from_playlist(item["id"])
                total_pruned += 1
        await progress(
            10 + ((i + 1) / len(exports)) * 85,
            f"Pruned {pl['snippet']['title']}",
        )

    await progress(100.0, f"Pruned {total_pruned} watched videos from {len(exports)} playlists")


async def handle_create_playlist(params, progress):
    from youtube_helper.config.settings import Settings

    settings = Settings()
    await progress(30.0, "Creating playlist...")
    _, client = _get_youtube_client(str(settings.db_path))
    client.create_playlist(
        params["title"],
        description=params.get("description", ""),
        privacy=params.get("privacy", "private"),
    )
    await progress(100.0, f"Created '{params['title']}'")


async def handle_delete_playlist(params, progress):
    from youtube_helper.config.settings import Settings

    settings = Settings()
    await progress(30.0, "Deleting playlist...")
    youtube, _ = _get_youtube_client(str(settings.db_path))
    youtube.playlists().delete(id=params["playlist_id"]).execute()
    # Also remove from local DB
    from youtube_helper.db.connection import get_connection

    conn = get_connection(str(settings.db_path))
    conn.execute("DELETE FROM playlist_videos WHERE playlist_id = ?", (params["playlist_id"],))
    conn.execute("DELETE FROM playlists WHERE id = ?", (params["playlist_id"],))
    conn.commit()
    conn.close()
    await progress(100.0, "Playlist deleted")


async def handle_add_videos(params, progress):
    from youtube_helper.config.settings import Settings

    settings = Settings()
    _, client = _get_youtube_client(str(settings.db_path))
    video_ids = params["video_ids"]
    for i, vid in enumerate(video_ids):
        client.add_to_playlist(params["playlist_id"], vid)
        await progress((i + 1) / len(video_ids) * 100, f"Added {i+1}/{len(video_ids)}")


async def handle_remove_video(params, progress):
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    db_path = str(settings.db_path)
    _, client = _get_youtube_client(db_path)

    # Find playlist_item_id from DB
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT playlist_item_id FROM playlist_videos WHERE playlist_id = ? AND video_id = ?",
        (params["playlist_id"], params["video_id"]),
    ).fetchone()
    conn.close()

    if row and row["playlist_item_id"]:
        await progress(50.0, "Removing from YouTube...")
        client.remove_from_playlist(row["playlist_item_id"])

    conn = get_connection(db_path)
    conn.execute(
        "DELETE FROM playlist_videos WHERE playlist_id = ? AND video_id = ?",
        (params["playlist_id"], params["video_id"]),
    )
    conn.commit()
    conn.close()
    await progress(100.0, "Video removed")


async def handle_reorder(params, progress):
    from youtube_helper.db.connection import get_connection
    from youtube_helper.config.settings import Settings

    settings = Settings()
    db_path = str(settings.db_path)
    conn = get_connection(db_path)
    for i, vid in enumerate(params["video_ids"]):
        conn.execute(
            "UPDATE playlist_videos SET position = ? WHERE playlist_id = ? AND video_id = ?",
            (i, params["playlist_id"], vid),
        )
    conn.commit()
    conn.close()
    await progress(100.0, "Reorder saved")


async def handle_like(params, progress):
    from youtube_helper.config.settings import Settings

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    await progress(50.0, "Liking video...")
    youtube.videos().rate(id=params["video_id"], rating="like").execute()

    from youtube_helper.db.connection import get_connection

    conn = get_connection(str(settings.db_path))
    conn.execute(
        "INSERT OR REPLACE INTO liked_videos (video_id, liked_at) VALUES (?, datetime('now'))",
        (params["video_id"],),
    )
    conn.commit()
    conn.close()
    await progress(100.0, "Video liked")


async def handle_unlike(params, progress):
    from youtube_helper.config.settings import Settings

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    await progress(50.0, "Removing like...")
    youtube.videos().rate(id=params["video_id"], rating="none").execute()

    from youtube_helper.db.connection import get_connection

    conn = get_connection(str(settings.db_path))
    conn.execute("DELETE FROM liked_videos WHERE video_id = ?", (params["video_id"],))
    conn.commit()
    conn.close()
    await progress(100.0, "Like removed")
```

Wire handlers in `app.py` lifespan:
```python
from youtube_helper.web.handlers import register_all_handlers
# Inside lifespan, after creating processor:
register_all_handlers(processor)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `pytest -v`
Expected: All pass

**Step 6: Commit**

```bash
git add src/youtube_helper/web/handlers.py tests/test_handlers.py src/youtube_helper/web/app.py
git commit -m "feat: operation handlers for all queue operation types"
```

---

### Task 9: `yt web` CLI Command + Production Static Serving

**Files:**
- Create: `src/youtube_helper/cli/web.py`
- Modify: `src/youtube_helper/cli/main.py` (register command)
- Modify: `src/youtube_helper/web/app.py` (add static file serving)
- Create: `tests/test_web_cli.py`

**Context:** The `yt web` command starts the FastAPI server and opens the browser. In production mode, it serves the built React frontend from `frontend/dist/` as static files. This task also updates the Makefile with `dev` and `build-ui` targets.

**Step 1: Write failing test**

```python
# tests/test_web_cli.py
from unittest.mock import patch

from youtube_helper.cli.main import cli


class TestWebCli:
    def test_web_command_exists(self, runner):
        result = runner.invoke(cli, ["web", "--help"])
        assert result.exit_code == 0
        assert "Start the web dashboard" in result.output

    def test_web_command_has_port_option(self, runner):
        result = runner.invoke(cli, ["web", "--help"])
        assert "--port" in result.output

    def test_web_command_has_no_browser_option(self, runner):
        result = runner.invoke(cli, ["web", "--help"])
        assert "--no-browser" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_cli.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/youtube_helper/cli/web.py
import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--port", default=8000, help="Port to run the server on.")
@click.option("--no-browser", is_flag=True, help="Don't open the browser automatically.")
@click.option("--dev", is_flag=True, help="Run in development mode (no static serving).")
def web(port: int, no_browser: bool, dev: bool) -> None:
    """Start the web dashboard server."""
    import uvicorn

    from youtube_helper.config.settings import Settings
    from youtube_helper.db.migrations import run_migrations

    settings = Settings()
    settings.ensure_dirs()
    run_migrations(str(settings.db_path))

    console.print(Panel(
        f"[cyan]Starting YouTube Helper dashboard on "
        f"[bold]http://localhost:{port}[/bold][/cyan]",
        title="[bold]Web Dashboard[/bold]",
        border_style="cyan",
    ))

    if not no_browser and not dev:
        import threading
        import time
        import webbrowser

        def open_browser():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "youtube_helper.web.app:create_app",
        host="0.0.0.0",
        port=port,
        reload=dev,
        factory=True,
    )
```

Register in `main.py`:
```python
from youtube_helper.cli.web import web
cli.add_command(web)
```

Update `app.py` to serve static files when the frontend build exists:
```python
# At the end of create_app, before return:
from pathlib import Path
frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    # Serve index.html for all non-API routes (SPA fallback)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        from fastapi.responses import FileResponse
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")

    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_cli.py -v`
Expected: PASS

**Step 5: Update Makefile**

Add these targets to `Makefile`:

```makefile
dev: ## Run API and frontend dev servers concurrently
	@echo "Starting FastAPI on :8000 and Vite on :5173..."
	@(cd frontend && npm run dev) & yt web --dev --no-browser --port 8000

build-ui: ## Build the frontend for production
	cd frontend && npm run build

run: ## Start the production server (API + built frontend)
	yt web
```

**Step 6: Commit**

```bash
git add src/youtube_helper/cli/web.py src/youtube_helper/cli/main.py src/youtube_helper/web/app.py tests/test_web_cli.py Makefile
git commit -m "feat: yt web CLI command with static serving and Makefile targets"
```

---

### Task 10: Frontend Scaffolding — Vite + React + MUI + Router + Layout

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/theme.ts`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/pages/Dashboard.tsx` (placeholder)

**Context:** This creates the React frontend with MUI theming, React Router, TanStack Query, and the main layout with sidebar navigation + top bar. All page placeholders will be filled in subsequent tasks. The Vite dev server proxies `/api` to FastAPI on port 8000.

**Step 1: Initialize frontend with test dependencies**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install @mui/material @mui/icons-material @emotion/react @emotion/styled
npm install react-router-dom @tanstack/react-query
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom msw
```

Add to `frontend/vite.config.ts`:
```typescript
/// <reference types="vitest" />
// In defineConfig:
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: './src/test/setup.ts',
},
```

Create test setup:
```typescript
// frontend/src/test/setup.ts
import '@testing-library/jest-dom/vitest'
```

Create MSW handlers for API mocking:
```typescript
// frontend/src/test/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/health', () => HttpResponse.json({ status: 'ok', version: '0.1.0' })),
  http.get('/api/playlists', () => HttpResponse.json({ playlists: [] })),
  http.get('/api/watch-later', () => HttpResponse.json({ videos: [] })),
  http.get('/api/videos/liked', () => HttpResponse.json({ videos: [] })),
  http.get('/api/auth/status', () =>
    HttpResponse.json({ authenticated: false, has_client_secret: false, has_token: false })
  ),
  http.get('/api/queue', () => HttpResponse.json({ operations: [] })),
  http.get('/api/search', ({ request }) => {
    const url = new URL(request.url)
    return HttpResponse.json({ query: url.searchParams.get('q'), results: [] })
  }),
  http.post('/api/sync', () => HttpResponse.json({ operation_id: 1, message: 'Sync queued' })),
]
```

```typescript
// frontend/src/test/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

Update `frontend/src/test/setup.ts`:
```typescript
import '@testing-library/jest-dom/vitest'
import { server } from './server'
import { beforeAll, afterAll, afterEach } from 'vitest'

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

**Step 2: Configure Vite proxy**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 3: Create MUI theme**

```typescript
// frontend/src/theme.ts
import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#ff0000' },  // YouTube red
    secondary: { main: '#aaa' },
    background: {
      default: '#0f0f0f',
      paper: '#1a1a1a',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
})

export default theme
```

**Step 4: Create Layout component with sidebar**

```tsx
// frontend/src/components/Layout.tsx
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  AppBar, Toolbar, Typography, IconButton,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  PlaylistPlay,
  WatchLater,
  Search as SearchIcon,
  ThumbUp,
  Settings,
  Menu as MenuIcon,
} from '@mui/icons-material'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useState } from 'react'

const DRAWER_WIDTH = 240

const NAV_ITEMS = [
  { label: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { label: 'Playlists', icon: <PlaylistPlay />, path: '/playlists' },
  { label: 'Watch Later', icon: <WatchLater />, path: '/watch-later' },
  { label: 'Search', icon: <SearchIcon />, path: '/search' },
  { label: 'Liked Videos', icon: <ThumbUp />, path: '/liked' },
  { label: 'Settings', icon: <Settings />, path: '/settings' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          YT Helper
        </Typography>
      </Toolbar>
      <List>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname === item.path}
            onClick={() => { navigate(item.path); setMobileOpen(false) }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            YouTube Helper
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        {drawer}
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Outlet />
      </Box>
    </Box>
  )
}
```

**Step 5: Create App with Router**

```tsx
// frontend/src/App.tsx
import { ThemeProvider, CssBaseline } from '@mui/material'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import theme from './theme'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              {/* More routes added in subsequent tasks */}
            </Route>
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

**Step 6: Create placeholder Dashboard**

```tsx
// frontend/src/pages/Dashboard.tsx
import { Typography, Box } from '@mui/material'

export default function Dashboard() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Dashboard</Typography>
      <Typography color="text.secondary">Loading...</Typography>
    </Box>
  )
}
```

**Step 7: Write component test for Layout**

```tsx
// frontend/src/components/__tests__/Layout.test.tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import Layout from '../Layout'

function renderWithProviders(ui: React.ReactElement, route = '/') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={[route]}>
          {ui}
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('Layout', () => {
  it('renders the sidebar with navigation items', () => {
    renderWithProviders(<Layout />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Playlists')).toBeInTheDocument()
    expect(screen.getByText('Watch Later')).toBeInTheDocument()
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByText('Liked Videos')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders the app title', () => {
    renderWithProviders(<Layout />)
    expect(screen.getByText('YouTube Helper')).toBeInTheDocument()
  })
})
```

**Step 8: Run test to verify it fails**

Run: `cd frontend && npx vitest run`
Expected: FAIL (Layout not yet importing correctly or missing providers)

**Step 9: Fix any issues and verify test passes**

Run: `cd frontend && npx vitest run`
Expected: PASS

**Step 10: Verify it runs visually**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173` — should show dark theme with sidebar and "Dashboard" heading.

**Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffolding with Vite, React, MUI, Router, layout, and tests"
```

---

### Task 11: Frontend — API Client + useSSE Hook + React Query Hooks

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/hooks/useSSE.ts`
- Create: `frontend/src/hooks/useApi.ts`

**Context:** Centralized API client with typed fetch wrappers. The `useSSE` hook creates an `EventSource` connection to `/api/events` and dispatches events to callbacks. React Query hooks wrap API calls for each resource type. All pages will import from these hooks.

**Step 1: Create API client**

```typescript
// frontend/src/api/client.ts
const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export const api = {
  // Health
  health: () => request<{ status: string; version: string }>('/health'),

  // Auth
  authStatus: () => request<{
    authenticated: boolean; has_client_secret: boolean; has_token: boolean
  }>('/auth/status'),

  // Playlists
  listPlaylists: () => request<{ playlists: Playlist[] }>('/playlists'),
  getPlaylistVideos: (id: string) =>
    request<{ playlist: Playlist; videos: Video[] }>(`/playlists/${id}/videos`),
  createPlaylist: (data: { title: string; privacy?: string }) =>
    request<QueuedOp>('/playlists', { method: 'POST', body: JSON.stringify(data) }),
  deletePlaylist: (id: string) =>
    request<QueuedOp>(`/playlists/${id}`, { method: 'DELETE' }),
  addVideos: (playlistId: string, videoIds: string[]) =>
    request<QueuedOp>(`/playlists/${playlistId}/videos`, {
      method: 'POST', body: JSON.stringify({ video_ids: videoIds }),
    }),
  removeVideo: (playlistId: string, videoId: string) =>
    request<QueuedOp>(`/playlists/${playlistId}/videos/${videoId}`, { method: 'DELETE' }),
  reorderPlaylist: (playlistId: string, videoIds: string[]) =>
    request<QueuedOp>(`/playlists/${playlistId}/reorder`, {
      method: 'PUT', body: JSON.stringify({ video_ids: videoIds }),
    }),

  // Videos
  likedVideos: () => request<{ videos: Video[] }>('/videos/liked'),
  likeVideo: (id: string) =>
    request<QueuedOp>(`/videos/${id}/like`, { method: 'POST' }),
  unlikeVideo: (id: string) =>
    request<QueuedOp>(`/videos/${id}/like`, { method: 'DELETE' }),

  // Watch Later
  watchLater: () => request<{ videos: Video[] }>('/watch-later'),
  watchLaterWatched: (threshold: number) =>
    request<{ videos: Video[] }>(`/watch-later/watched?threshold=${threshold}`),
  watchLaterUnwatched: (threshold: number) =>
    request<{ videos: Video[] }>(`/watch-later/unwatched?threshold=${threshold}`),
  scrapeWatchLater: () =>
    request<QueuedOp>('/watch-later/scrape', { method: 'POST' }),
  exportWatchLater: (data: { target: string; threshold: number }) =>
    request<QueuedOp>('/watch-later/export', { method: 'POST', body: JSON.stringify(data) }),
  purgeWatchLater: (data: { threshold: number }) =>
    request<QueuedOp>('/watch-later/purge', { method: 'POST', body: JSON.stringify(data) }),
  pruneExports: () =>
    request<QueuedOp>('/watch-later/prune-exports', { method: 'POST' }),

  // Search
  search: (q: string, threshold?: number) =>
    request<{ query: string; results: SearchResult[] }>(
      `/search?q=${encodeURIComponent(q)}${threshold ? `&threshold=${threshold}` : ''}`
    ),

  // Sync
  sync: () => request<QueuedOp>('/sync', { method: 'POST' }),

  // Queue
  listQueue: () => request<{ operations: QueueOp[] }>('/queue'),
  cancelOp: (id: number) => request<{ message: string }>(`/queue/${id}`, { method: 'DELETE' }),
  retryOp: (id: number) => request<{ message: string }>(`/queue/${id}/retry`, { method: 'POST' }),
  skipOp: (id: number) => request<{ message: string }>(`/queue/${id}/skip`, { method: 'POST' }),
}

// Types
export interface Playlist {
  id: string; title: string; description: string; privacy_status: string;
  video_count: number; source: string; last_synced: string;
}
export interface Video {
  id: string; title: string; channel_name: string; channel_id: string;
  duration: number; watch_progress: number; thumbnail_url: string;
  published_at: string; position?: number;
}
export interface SearchResult extends Partial<Video>, Partial<Playlist> {
  type: 'video' | 'playlist'; score: number;
}
export interface QueueOp {
  id: number; type: string; params: string; status: string;
  progress: number; message: string; error: string;
  created_at: string; started_at: string | null; completed_at: string | null;
}
export interface QueuedOp { operation_id: number; message: string }
```

**Step 2: Create useSSE hook**

```typescript
// frontend/src/hooks/useSSE.ts
import { useEffect, useRef, useCallback } from 'react'

interface SSEEvent {
  type: string
  operation_id?: number
  status?: string
  progress?: number
  message?: string
  error?: string
}

export function useSSE(onEvent: (event: SSEEvent) => void) {
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent
  const sourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const source = new EventSource('/api/events')
    sourceRef.current = source

    source.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SSEEvent
        onEventRef.current(data)
      } catch {
        // ignore parse errors
      }
    }

    source.onerror = () => {
      // EventSource auto-reconnects
    }

    return () => { source.close() }
  }, [])

  return sourceRef
}
```

**Step 3: Create React Query hooks**

```typescript
// frontend/src/hooks/useApi.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export const usePlaylists = () =>
  useQuery({ queryKey: ['playlists'], queryFn: api.listPlaylists })

export const usePlaylistVideos = (id: string) =>
  useQuery({ queryKey: ['playlist', id], queryFn: () => api.getPlaylistVideos(id) })

export const useWatchLater = () =>
  useQuery({ queryKey: ['watch-later'], queryFn: api.watchLater })

export const useWatchLaterWatched = (threshold: number) =>
  useQuery({
    queryKey: ['watch-later-watched', threshold],
    queryFn: () => api.watchLaterWatched(threshold),
  })

export const useWatchLaterUnwatched = (threshold: number) =>
  useQuery({
    queryKey: ['watch-later-unwatched', threshold],
    queryFn: () => api.watchLaterUnwatched(threshold),
  })

export const useLikedVideos = () =>
  useQuery({ queryKey: ['liked-videos'], queryFn: api.likedVideos })

export const useSearch = (q: string, threshold?: number) =>
  useQuery({
    queryKey: ['search', q, threshold],
    queryFn: () => api.search(q, threshold),
    enabled: q.length > 0,
  })

export const useAuthStatus = () =>
  useQuery({ queryKey: ['auth-status'], queryFn: api.authStatus })

export const useQueue = () =>
  useQuery({ queryKey: ['queue'], queryFn: api.listQueue, refetchInterval: 2000 })

// Mutations
export const useSync = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.sync,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const useScrape = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.scrapeWatchLater,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const useExportWL = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.exportWatchLater,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const usePurgeWL = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.purgeWatchLater,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const usePruneExports = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.pruneExports,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}
```

**Step 4: Write unit tests for API client**

```tsx
// frontend/src/api/__tests__/client.test.ts
import { describe, it, expect } from 'vitest'
import { api } from '../client'

describe('API client', () => {
  it('fetches health endpoint', async () => {
    const data = await api.health()
    expect(data.status).toBe('ok')
    expect(data.version).toBe('0.1.0')
  })

  it('fetches playlists', async () => {
    const data = await api.listPlaylists()
    expect(data.playlists).toEqual([])
  })

  it('fetches auth status', async () => {
    const data = await api.authStatus()
    expect(data).toHaveProperty('authenticated')
  })

  it('submits sync operation', async () => {
    const data = await api.sync()
    expect(data.operation_id).toBe(1)
    expect(data.message).toBe('Sync queued')
  })

  it('searches with query', async () => {
    const data = await api.search('test')
    expect(data.query).toBe('test')
    expect(data.results).toEqual([])
  })

  it('throws on HTTP error', async () => {
    // MSW doesn't have a handler for this, so it will fail
    await expect(api.getPlaylistVideos('nonexistent')).rejects.toThrow()
  })
})
```

**Step 5: Write unit test for useSSE hook**

```tsx
// frontend/src/hooks/__tests__/useSSE.test.ts
import { describe, it, expect, vi } from 'vitest'

// Test the hook logic conceptually - EventSource is not available in jsdom
// So we test the hook with a mock
describe('useSSE', () => {
  it('module exports useSSE function', async () => {
    const mod = await import('../useSSE')
    expect(typeof mod.useSSE).toBe('function')
  })
})
```

**Step 6: Write integration test for React Query hooks**

```tsx
// frontend/src/hooks/__tests__/useApi.test.tsx
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePlaylists, useAuthStatus, useQueue } from '../useApi'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('React Query hooks', () => {
  it('usePlaylists returns playlist data', async () => {
    const { result } = renderHook(() => usePlaylists(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.playlists).toEqual([])
  })

  it('useAuthStatus returns auth data', async () => {
    const { result } = renderHook(() => useAuthStatus(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.authenticated).toBe(false)
  })

  it('useQueue returns queue data', async () => {
    const { result } = renderHook(() => useQueue(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.operations).toEqual([])
  })
})
```

**Step 7: Run tests to verify they fail, then pass once implementation is done**

Run: `cd frontend && npx vitest run`
Expected: All pass (MSW mocks the API calls)

**Step 8: Verify frontend compiles**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no TypeScript errors

**Step 9: Commit**

```bash
git add frontend/src/api/ frontend/src/hooks/
git commit -m "feat: API client, useSSE hook, React Query hooks, and tests"
```

---

### Task 12: Frontend — Dashboard Page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

**Context:** The dashboard shows overview cards (playlist count, video count, Watch Later count, last sync), quick action buttons (Sync, Scrape), and a queue status summary. Uses React Query hooks from Task 11.

**Step 1: Implement Dashboard**

```tsx
// frontend/src/pages/Dashboard.tsx
import {
  Box, Card, CardContent, Typography, Grid, Button, Tooltip, Chip, Stack,
} from '@mui/material'
import { Sync, WatchLater, PlaylistPlay, VideoLibrary } from '@mui/icons-material'
import { usePlaylists, useWatchLater, useSync, useScrape, useQueue } from '../hooks/useApi'

export default function Dashboard() {
  const { data: playlistData } = usePlaylists()
  const { data: wlData } = useWatchLater()
  const { data: queueData } = useQueue()
  const syncMutation = useSync()
  const scrapeMutation = useScrape()

  const playlists = playlistData?.playlists ?? []
  const wlVideos = wlData?.videos ?? []
  const queue = queueData?.operations ?? []
  const activeOps = queue.filter(op => op.status === 'active')
  const pendingOps = queue.filter(op => op.status === 'pending')
  const totalVideos = playlists.reduce((sum, p) => sum + (p.video_count || 0), 0)

  const cards = [
    { label: 'Playlists', value: playlists.length, icon: <PlaylistPlay fontSize="large" /> },
    { label: 'Total Videos', value: totalVideos, icon: <VideoLibrary fontSize="large" /> },
    { label: 'Watch Later', value: wlVideos.length, icon: <WatchLater fontSize="large" /> },
  ]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Dashboard</Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {cards.map((card) => (
          <Grid item xs={12} sm={4} key={card.label}>
            <Card>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {card.icon}
                <Box>
                  <Typography variant="h4" fontWeight="bold">{card.value}</Typography>
                  <Typography color="text.secondary">{card.label}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Typography variant="h5" gutterBottom>Quick Actions</Typography>
      <Stack direction="row" spacing={2} sx={{ mb: 4 }}>
        <Tooltip title="Pull all playlist and video metadata from YouTube into your local database. This fetches metadata only — no video files are downloaded. Uses YouTube Data API quota (1 unit per page).">
          <span>
            <Button
              variant="contained"
              startIcon={<Sync />}
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
            >
              Sync Playlists
            </Button>
          </span>
        </Tooltip>
        <Tooltip title="Launch Chrome using your logged-in profile to scroll through your Watch Later playlist and extract video metadata plus watch progress from the thumbnail progress bars. Uses zero API quota.">
          <span>
            <Button
              variant="contained"
              color="secondary"
              startIcon={<WatchLater />}
              onClick={() => scrapeMutation.mutate()}
              disabled={scrapeMutation.isPending}
            >
              Scrape Watch Later
            </Button>
          </span>
        </Tooltip>
      </Stack>

      {(activeOps.length > 0 || pendingOps.length > 0) && (
        <Box>
          <Typography variant="h5" gutterBottom>Queue Status</Typography>
          {activeOps.map(op => (
            <Chip
              key={op.id}
              label={`${op.type}: ${op.message || 'Running...'} (${op.progress.toFixed(0)}%)`}
              color="primary"
              sx={{ mr: 1 }}
            />
          ))}
          {pendingOps.length > 0 && (
            <Chip label={`${pendingOps.length} pending`} variant="outlined" />
          )}
        </Box>
      )}
    </Box>
  )
}
```

**Step 2: Write integration test for Dashboard**

```tsx
// frontend/src/pages/__tests__/Dashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import Dashboard from '../Dashboard'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'

function renderDashboard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('Dashboard', () => {
  it('renders the dashboard heading', () => {
    renderDashboard()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('shows stat cards', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('Playlists')).toBeInTheDocument()
      expect(screen.getByText('Total Videos')).toBeInTheDocument()
      expect(screen.getByText('Watch Later')).toBeInTheDocument()
    })
  })

  it('shows quick action buttons', () => {
    renderDashboard()
    expect(screen.getByText('Sync Playlists')).toBeInTheDocument()
    expect(screen.getByText('Scrape Watch Later')).toBeInTheDocument()
  })

  it('displays playlist count from API', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({ playlists: [
          { id: 'PL1', title: 'Test', video_count: 5 },
          { id: 'PL2', title: 'Test2', video_count: 10 },
        ] })
      ),
    )
    renderDashboard()
    await waitFor(() => expect(screen.getByText('2')).toBeInTheDocument())
  })

  it('sync button triggers mutation', async () => {
    const user = userEvent.setup()
    renderDashboard()
    await user.click(screen.getByText('Sync Playlists'))
    // Button should be disabled while mutation is pending
  })
})
```

**Step 3: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/pages/__tests__/Dashboard.test.tsx`
Expected: FAIL (Dashboard not yet implemented)

**Step 4: Implement Dashboard (code from Step 1 above)**

**Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/__tests__/Dashboard.test.tsx`
Expected: PASS

**Step 6: Verify it renders visually**

Start both servers (`make dev`), navigate to `http://localhost:5173`. Dashboard should show cards with counts and action buttons with tooltip descriptions.

**Step 7: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/__tests__/
git commit -m "feat: dashboard page with stats cards, quick actions, queue status, and tests"
```

---

### Task 13: Frontend — Playlists + PlaylistDetail Pages

**Files:**
- Create: `frontend/src/pages/Playlists.tsx`
- Create: `frontend/src/pages/PlaylistDetail.tsx`
- Create: `frontend/src/components/VideoTable.tsx`
- Create: `frontend/src/components/ConfirmDialog.tsx`
- Modify: `frontend/src/App.tsx` (add routes)

**Context:** Playlists page shows a card grid of all playlists. Clicking a playlist navigates to PlaylistDetail, which shows a sortable video table with per-video action buttons (remove, like/unlike, copy to another playlist). The VideoTable component is shared with Watch Later and Liked Videos pages. ConfirmDialog is used for destructive actions across the app.

Implement the `VideoTable` with columns: #, Title, Channel, Duration, Progress, Actions. The `ConfirmDialog` wraps MUI Dialog with a confirm/cancel pattern and explanatory text describing what the action will do.

The Playlists page includes a "Create Playlist" button with a dialog. Each playlist card has a delete button that shows a ConfirmDialog.

Add routes to `App.tsx`:
```tsx
<Route path="/playlists" element={<Playlists />} />
<Route path="/playlists/:id" element={<PlaylistDetail />} />
```

**Key action descriptions to include:**
- **Create Playlist:** "Create a new private playlist on your YouTube account. This uses 50 API quota units."
- **Delete Playlist:** "Permanently delete this playlist from YouTube. All videos in the playlist will be unlinked but not deleted from YouTube. This cannot be undone."
- **Remove Video:** "Remove this video from the playlist. The video itself is not deleted from YouTube."
- **Like Video:** "Add this video to your YouTube Liked Videos. Uses 50 API quota units."

**TDD — Write these tests first, verify FAIL, then implement:**

```tsx
// frontend/src/components/__tests__/VideoTable.test.tsx
import { render, screen } from '@testing-library/react'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import VideoTable from '../VideoTable'

describe('VideoTable', () => {
  const videos = [
    { id: 'V1', title: 'Video One', channel_name: 'Ch A', duration: 600, watch_progress: 75 },
    { id: 'V2', title: 'Video Two', channel_name: 'Ch B', duration: 120, watch_progress: 0 },
  ]

  it('renders video titles', () => {
    render(<ThemeProvider theme={theme}><VideoTable videos={videos} /></ThemeProvider>)
    expect(screen.getByText('Video One')).toBeInTheDocument()
    expect(screen.getByText('Video Two')).toBeInTheDocument()
  })

  it('renders channel names', () => {
    render(<ThemeProvider theme={theme}><VideoTable videos={videos} /></ThemeProvider>)
    expect(screen.getByText('Ch A')).toBeInTheDocument()
  })

  it('renders progress for videos with watch progress', () => {
    render(<ThemeProvider theme={theme}><VideoTable videos={videos} /></ThemeProvider>)
    expect(screen.getByText('75%')).toBeInTheDocument()
  })
})
```

```tsx
// frontend/src/components/__tests__/ConfirmDialog.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import ConfirmDialog from '../ConfirmDialog'

describe('ConfirmDialog', () => {
  it('renders title and description', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Delete Playlist"
        description="This cannot be undone."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByText('Delete Playlist')).toBeInTheDocument()
    expect(screen.getByText('This cannot be undone.')).toBeInTheDocument()
  })

  it('calls onConfirm when confirm clicked', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(
      <ConfirmDialog open={true} title="Delete" description="Sure?"
        onConfirm={onConfirm} onCancel={vi.fn()} />
    )
    await user.click(screen.getByText('Confirm'))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('calls onCancel when cancel clicked', async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()
    render(
      <ConfirmDialog open={true} title="Delete" description="Sure?"
        onConfirm={vi.fn()} onCancel={onCancel} />
    )
    await user.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledOnce()
  })
})
```

```tsx
// frontend/src/pages/__tests__/Playlists.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import Playlists from '../Playlists'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'

function renderPlaylists() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter><Playlists /></MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('Playlists', () => {
  it('renders the page heading', () => {
    renderPlaylists()
    expect(screen.getByText('Playlists')).toBeInTheDocument()
  })

  it('displays playlists from API', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({ playlists: [
          { id: 'PL1', title: 'My Favorites', video_count: 42, privacy_status: 'private' },
        ] })
      ),
    )
    renderPlaylists()
    await waitFor(() => expect(screen.getByText('My Favorites')).toBeInTheDocument())
  })

  it('shows create playlist button', () => {
    renderPlaylists()
    expect(screen.getByText('Create Playlist')).toBeInTheDocument()
  })
})
```

Run tests: `cd frontend && npx vitest run`
Expected: All pass after implementation

**Commit:**

```bash
git add frontend/src/pages/Playlists.tsx frontend/src/pages/PlaylistDetail.tsx frontend/src/components/VideoTable.tsx frontend/src/components/ConfirmDialog.tsx frontend/src/App.tsx frontend/src/components/__tests__/ frontend/src/pages/__tests__/
git commit -m "feat: playlists page, playlist detail, video table, confirm dialog, and tests"
```

---

### Task 14: Frontend — Watch Later Page

**Files:**
- Create: `frontend/src/pages/WatchLater.tsx`
- Create: `frontend/src/components/ProgressBar.tsx`
- Modify: `frontend/src/App.tsx` (add route)

**Context:** The Watch Later page shows all videos from the WL playlist with visual progress bars. It includes a threshold slider to filter watched/unwatched. Action buttons at the top: Scrape, Export, Purge, Prune Exports — each with a tooltip and optional confirmation dialog. During operations, an SSE-connected progress panel shows real-time status.

**Key action descriptions:**
- **Scrape:** "Launch Chrome to scan your Watch Later playlist. This opens a browser window using your Chrome profile and scrolls through Watch Later to detect video metadata and watch progress from thumbnail progress bars. Uses zero API quota."
- **Export:** "Create a dated private playlist with all Watch Later videos, append to the master archive, copy unwatched videos to your target playlist, and remove watched videos from the local database. This uses API quota proportional to the number of videos (50 units per video added)."
- **Purge:** "Open Chrome and automatically remove all watched videos from your Watch Later playlist on YouTube. This scrolls through Watch Later, finds videos you've watched above the threshold, and clicks 'Remove from Watch Later' on each. Uses zero API quota."
- **Prune Exports:** "Scan all Watch Later Export playlists and remove videos you've since watched. Helps keep export playlists clean over time. Uses API quota for list + remove operations."

The threshold slider updates a query parameter and re-fetches watched/unwatched counts.

Add route: `<Route path="/watch-later" element={<WatchLater />} />`

**TDD — Write these tests first, verify FAIL, then implement:**

```tsx
// frontend/src/components/__tests__/ProgressBar.test.tsx
import { render, screen } from '@testing-library/react'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import ProgressBar from '../ProgressBar'

describe('ProgressBar', () => {
  it('renders with percentage text', () => {
    render(<ThemeProvider theme={theme}><ProgressBar value={75} /></ThemeProvider>)
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('renders 0% progress', () => {
    render(<ThemeProvider theme={theme}><ProgressBar value={0} /></ThemeProvider>)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })
})
```

```tsx
// frontend/src/pages/__tests__/WatchLater.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import WatchLater from '../WatchLater'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'

function renderWatchLater() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter><WatchLater /></MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('WatchLater', () => {
  it('renders the page heading', () => {
    renderWatchLater()
    expect(screen.getByText('Watch Later')).toBeInTheDocument()
  })

  it('shows action buttons with descriptions', () => {
    renderWatchLater()
    expect(screen.getByText('Scrape')).toBeInTheDocument()
    expect(screen.getByText('Export')).toBeInTheDocument()
    expect(screen.getByText('Purge')).toBeInTheDocument()
    expect(screen.getByText('Prune Exports')).toBeInTheDocument()
  })

  it('displays videos from API', async () => {
    server.use(
      http.get('/api/watch-later', () =>
        HttpResponse.json({ videos: [
          { id: 'V1', title: 'Test Video', channel_name: 'Test Ch', watch_progress: 60 },
        ] })
      ),
    )
    renderWatchLater()
    await waitFor(() => expect(screen.getByText('Test Video')).toBeInTheDocument())
  })

  it('has a threshold slider', () => {
    renderWatchLater()
    expect(screen.getByText(/threshold/i)).toBeInTheDocument()
  })
})
```

Run tests: `cd frontend && npx vitest run`
Expected: All pass after implementation

**Commit:**

```bash
git add frontend/src/pages/WatchLater.tsx frontend/src/components/ProgressBar.tsx frontend/src/App.tsx frontend/src/components/__tests__/ frontend/src/pages/__tests__/
git commit -m "feat: watch later page with progress bars, threshold slider, action buttons, and tests"
```

---

### Task 15: Frontend — Search Page

**Files:**
- Create: `frontend/src/pages/Search.tsx`
- Modify: `frontend/src/App.tsx` (add route)

**Context:** Search page has a text input that triggers fuzzy search via `GET /api/search?q=`. Results are grouped into "Videos" and "Playlists" sections. Each result shows match score, title, and channel/video count. Clicking a video result shows its details; clicking a playlist navigates to PlaylistDetail. Debounce the search input to avoid excessive API calls.

Add tooltip: "Search uses fuzzy matching across all video titles, channel names, and playlist names in your local database. Higher threshold = stricter matching. No API quota used."

Add route: `<Route path="/search" element={<Search />} />`

**TDD — Write these tests first, verify FAIL, then implement:**

```tsx
// frontend/src/pages/__tests__/Search.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import Search from '../Search'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'

function renderSearch() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter><Search /></MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('Search', () => {
  it('renders search input', () => {
    renderSearch()
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument()
  })

  it('shows description text about fuzzy matching', () => {
    renderSearch()
    expect(screen.getByText(/fuzzy matching/i)).toBeInTheDocument()
  })

  it('displays results when search returns data', async () => {
    server.use(
      http.get('/api/search', () =>
        HttpResponse.json({
          query: 'python',
          results: [
            { type: 'video', id: 'V1', title: 'Python Tutorial', channel_name: 'Ch', score: 90 },
            { type: 'playlist', id: 'PL1', title: 'Python Playlist', score: 85 },
          ],
        })
      ),
    )
    const user = userEvent.setup()
    renderSearch()
    await user.type(screen.getByPlaceholderText(/search/i), 'python')
    await waitFor(() => expect(screen.getByText('Python Tutorial')).toBeInTheDocument())
    expect(screen.getByText('Python Playlist')).toBeInTheDocument()
  })
})
```

Run tests: `cd frontend && npx vitest run`
Expected: All pass after implementation

**Commit:**

```bash
git add frontend/src/pages/Search.tsx frontend/src/App.tsx frontend/src/pages/__tests__/
git commit -m "feat: search page with fuzzy matching, grouped results, and tests"
```

---

### Task 16: Frontend — Liked Videos + Settings Pages

**Files:**
- Create: `frontend/src/pages/LikedVideos.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/App.tsx` (add routes)

**Context:** Liked Videos shows a grid/list of liked videos from `GET /api/videos/liked`. Each video has an unlike button. Settings page shows auth status (from `/api/auth/status`), link to run `yt auth setup` in CLI if not authenticated, and a queue operations summary.

**Settings descriptions:**
- **Auth Status:** "Shows whether you have valid YouTube API credentials. If unauthenticated, run `yt auth setup` in your terminal to configure OAuth."
- **Sync:** "Sync pulls metadata for all your YouTube playlists into the local database. Run this periodically to keep your data up to date."

Add routes:
```tsx
<Route path="/liked" element={<LikedVideos />} />
<Route path="/settings" element={<Settings />} />
```

**TDD — Write these tests first, verify FAIL, then implement:**

```tsx
// frontend/src/pages/__tests__/LikedVideos.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import LikedVideos from '../LikedVideos'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'

function renderLikedVideos() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter><LikedVideos /></MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('LikedVideos', () => {
  it('renders the page heading', () => {
    renderLikedVideos()
    expect(screen.getByText('Liked Videos')).toBeInTheDocument()
  })

  it('displays liked videos from API', async () => {
    server.use(
      http.get('/api/videos/liked', () =>
        HttpResponse.json({ videos: [
          { id: 'V1', title: 'Liked Video', channel_name: 'Ch', liked_at: '2026-01-01' },
        ] })
      ),
    )
    renderLikedVideos()
    await waitFor(() => expect(screen.getByText('Liked Video')).toBeInTheDocument())
  })
})
```

```tsx
// frontend/src/pages/__tests__/Settings.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import Settings from '../Settings'

function renderSettings() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter><Settings /></MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('Settings', () => {
  it('renders the page heading', () => {
    renderSettings()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('shows auth status section', async () => {
    renderSettings()
    await waitFor(() => expect(screen.getByText(/authentication/i)).toBeInTheDocument())
  })

  it('shows setup instructions when not authenticated', async () => {
    renderSettings()
    await waitFor(() => expect(screen.getByText(/yt auth setup/i)).toBeInTheDocument())
  })
})
```

Run tests: `cd frontend && npx vitest run`
Expected: All pass after implementation

**Commit:**

```bash
git add frontend/src/pages/LikedVideos.tsx frontend/src/pages/Settings.tsx frontend/src/App.tsx frontend/src/pages/__tests__/
git commit -m "feat: liked videos and settings pages with tests"
```

---

### Task 17: Frontend — Queue Panel + Toast Notifications

**Files:**
- Create: `frontend/src/components/QueuePanel.tsx`
- Create: `frontend/src/components/ToastProvider.tsx`
- Modify: `frontend/src/components/Layout.tsx` (add queue drawer + toast)
- Modify: `frontend/src/App.tsx` (wrap with ToastProvider)

**Context:** The QueuePanel is a collapsible bottom drawer that shows all queue operations. Active operations show a progress bar and message. Failed operations show red error text with retry/skip buttons. Pending operations show position in queue with a cancel button. The queue panel icon in the top bar shows a badge with the count of active+pending operations.

ToastProvider uses MUI Snackbar for success/error notifications on mutations. All mutation hooks should trigger a toast on success/error.

The SSE hook feeds queue events into the queue panel and triggers React Query invalidation so pages refresh when operations complete.

**Action descriptions in queue panel:**
- **Retry:** "Re-run this failed operation from the beginning."
- **Skip:** "Mark this operation as skipped and continue with the next one in the queue."
- **Cancel:** "Remove this operation from the queue before it starts."

**TDD — Write these tests first, verify FAIL, then implement:**

```tsx
// frontend/src/components/__tests__/QueuePanel.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { ThemeProvider } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import theme from '../../theme'
import QueuePanel from '../QueuePanel'

const mockOperations = [
  { id: 1, type: 'sync', status: 'active', progress: 50, message: 'Syncing...', error: '', params: '{}', created_at: '', started_at: '', completed_at: null },
  { id: 2, type: 'scrape', status: 'pending', progress: 0, message: '', error: '', params: '{}', created_at: '', started_at: null, completed_at: null },
  { id: 3, type: 'export', status: 'failed', progress: 30, message: '', error: 'Network error', params: '{}', created_at: '', started_at: '', completed_at: '' },
]

function renderQueuePanel(operations = mockOperations) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <QueuePanel operations={operations} open={true} onClose={vi.fn()} />
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('QueuePanel', () => {
  it('shows active operation with progress', () => {
    renderQueuePanel()
    expect(screen.getByText(/sync/i)).toBeInTheDocument()
    expect(screen.getByText('Syncing...')).toBeInTheDocument()
  })

  it('shows pending operations', () => {
    renderQueuePanel()
    expect(screen.getByText(/scrape/i)).toBeInTheDocument()
  })

  it('shows failed operations with error', () => {
    renderQueuePanel()
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('has retry button for failed operations', () => {
    renderQueuePanel()
    expect(screen.getByText('Retry')).toBeInTheDocument()
  })

  it('has skip button for failed operations', () => {
    renderQueuePanel()
    expect(screen.getByText('Skip')).toBeInTheDocument()
  })

  it('has cancel button for pending operations', () => {
    renderQueuePanel()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })
})
```

```tsx
// frontend/src/components/__tests__/ToastProvider.test.tsx
import { render, screen } from '@testing-library/react'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import { ToastProvider, useToast } from '../ToastProvider'

function TestComponent() {
  const toast = useToast()
  return <button onClick={() => toast.success('It worked!')}>Show Toast</button>
}

describe('ToastProvider', () => {
  it('provides toast context', () => {
    render(
      <ThemeProvider theme={theme}>
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      </ThemeProvider>
    )
    expect(screen.getByText('Show Toast')).toBeInTheDocument()
  })
})
```

Run tests: `cd frontend && npx vitest run`
Expected: All pass after implementation

**Commit:**

```bash
git add frontend/src/components/QueuePanel.tsx frontend/src/components/ToastProvider.tsx frontend/src/components/__tests__/ frontend/src/components/Layout.tsx frontend/src/App.tsx
git commit -m "feat: queue panel with real-time progress, toasts, operation controls, and tests"
```

---

### Task 18: Integration — Final Wiring + Makefile + Smoke Test

**Files:**
- Modify: `Makefile` (finalize dev/build/run targets)
- Modify: `pyproject.toml` (ensure all deps correct)
- Modify: `README.md` (add web dashboard section)

**Context:** Final integration task. Ensure `make dev` starts both servers, `make build-ui` builds the frontend, `yt web` serves everything. Run the full test suite. Add a web dashboard section to the README.

**Step 1: Finalize Makefile**

```makefile
dev: ## Run API + frontend dev servers
	@echo "Starting FastAPI on :8000 and Vite on :5173..."
	@trap 'kill 0' EXIT; \
	(yt web --dev --no-browser --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

build-ui: ## Build frontend for production
	cd frontend && npm install && npm run build

run: build-ui ## Build frontend and start production server
	yt web
```

**Step 2: Run full backend test suite**

Run: `pytest -v`
Expected: All tests pass

**Step 3: Build and verify frontend**

```bash
make build-ui
yt web --no-browser &
# Test health endpoint
curl http://localhost:8000/api/health
# Test SPA serving
curl -s http://localhost:8000/ | grep -q "YouTube Helper"
```

**Step 4: Update README**

Add a "Web Dashboard" section after the CLI Reference section:

```markdown
### Web Dashboard

Start the web UI:

\`\`\`bash
yt web                    # Build frontend + start server + open browser
yt web --port 3000        # Custom port
yt web --no-browser       # Don't auto-open browser
\`\`\`

For development with hot reload:

\`\`\`bash
make dev                  # Starts API on :8000, frontend on :5173
\`\`\`

The dashboard provides:
- **Dashboard** — Overview stats, quick sync/scrape buttons
- **Playlists** — Browse, create, delete playlists; manage videos
- **Watch Later** — View progress, export, purge, prune
- **Search** — Fuzzy search across all videos and playlists
- **Liked Videos** — View and manage liked videos
- **Settings** — Auth status and configuration
- **Operation Queue** — Track progress of all operations in real-time
```

**Step 5: Commit**

```bash
git add Makefile pyproject.toml README.md
git commit -m "feat: finalize web dashboard integration with Makefile and docs"
```

---

## Summary

| Task | Description | Backend Tests | Frontend Tests |
|------|-------------|--------------|----------------|
| 1 | FastAPI app foundation | 2 | — |
| 2 | Operation queue table + QueueManager | 7 | — |
| 3 | SSE event broadcaster | 2 | — |
| 4 | Auth, search, sync routes | 4 | — |
| 5 | Playlist CRUD routes | 8 | — |
| 6 | Video + Watch Later routes | 10 | — |
| 7 | Queue routes + processor | 7 | — |
| 8 | Operation handlers | 1 | — |
| 9 | `yt web` CLI command | 3 | — |
| 10 | Frontend scaffolding + layout | — | 2 (Layout) |
| 11 | API client + hooks | — | 10 (unit + integration) |
| 12 | Dashboard page | — | 5 (integration) |
| 13 | Playlists + detail pages | — | 9 (component + integration) |
| 14 | Watch Later page | — | 6 (component + integration) |
| 15 | Search page | — | 3 (integration) |
| 16 | Liked Videos + Settings | — | 5 (integration) |
| 17 | Queue panel + toasts | — | 7 (component) |
| 18 | Integration + Makefile | smoke | — |

**Total new backend tests:** ~44
**Total new frontend tests:** ~47
**Total tasks:** 18

**Test commands:**
- Backend: `pytest -v`
- Frontend: `cd frontend && npx vitest run`
- All: `make test` (update Makefile to run both)
