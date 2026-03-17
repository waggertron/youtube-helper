# Simplify App: Remove Queue, Rework Watch Later — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the queue/SSE infrastructure, replace with direct request/response for fast ops and simple asyncio.Task for slow ops. Replace Watch Later scraping with Google Takeout import. Keep Playwright only for purge.

**Architecture:** Fast operations (playlist CRUD, like/unlike) become synchronous route handlers. Slow operations (sync, purge) use a lightweight BackgroundTasks class that stores state in an app-level dict. Watch Later data comes from Google Takeout file upload instead of Playwright scraping.

**Tech Stack:** Python/FastAPI, SQLite, Playwright (purge only), React/TypeScript, React Query, Vite

**Design doc:** `docs/plans/2026-03-17-simplify-remove-queue-design.md`

---

### Task 1: Add BackgroundTasks Manager

A lightweight replacement for the queue system. Stores running task state in a dict. ~30 lines.

**Files:**
- Create: `src/youtube_helper/web/tasks.py`
- Test: `tests/test_background_tasks.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_background_tasks.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```python
# src/youtube_helper/web/tasks.py
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_background_tasks.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/youtube_helper/web/tasks.py tests/test_background_tasks.py
git commit -m "feat: add lightweight BackgroundTasks manager"
```

---

### Task 2: Rewrite Handlers as Direct Functions

Remove progress_callback signatures. Handlers become plain async functions that routes call directly. Keep the same business logic.

**Files:**
- Modify: `src/youtube_helper/web/handlers.py`
- Modify: `tests/test_handlers.py`

**Step 1: Write the failing tests**

Rewrite handler tests to call functions directly without progress callbacks. Focus on the fast operations first (playlist CRUD, like/unlike, reorder).

```python
# tests/test_handlers.py — replace existing content
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from youtube_helper.web.handlers import (
    handle_create_playlist,
    handle_delete_playlist,
    handle_add_videos,
    handle_remove_video,
    handle_reorder,
    handle_like,
    handle_unlike,
)


@pytest.fixture
def mock_settings(tmp_path):
    with patch("youtube_helper.web.handlers.Settings") as mock:
        settings = MagicMock()
        settings.db_path = str(tmp_path / "test.db")
        mock.return_value = settings
        yield settings


@pytest.mark.asyncio
async def test_handle_create_playlist(mock_settings):
    with patch("youtube_helper.web.handlers._get_youtube_client") as mock_yt:
        client = MagicMock()
        client.create_playlist.return_value = {"id": "PLnew", "snippet": {"title": "Test"}}
        mock_yt.return_value = client

        result = await handle_create_playlist(
            title="Test", description="desc", privacy="private"
        )
        assert result["id"] == "PLnew"
        client.create_playlist.assert_called_once_with("Test", "desc", "private")


@pytest.mark.asyncio
async def test_handle_like(mock_settings):
    with patch("youtube_helper.web.handlers._get_youtube_client") as mock_yt:
        client = MagicMock()
        videos_resource = MagicMock()
        rate_request = MagicMock()
        rate_request.execute.return_value = None
        videos_resource.rate.return_value = rate_request
        client.youtube.videos.return_value = videos_resource
        mock_yt.return_value = client

        result = await handle_like(video_id="abc123")
        assert result["video_id"] == "abc123"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_handlers.py -v`
Expected: FAIL — signatures don't match (current handlers take `params` dict + `progress` callback)

**Step 3: Rewrite handlers**

Rewrite `src/youtube_helper/web/handlers.py`:
- Remove `register_all_handlers()` function
- Remove `progress` callback parameter from all handlers
- Change handler signatures from `handle_x(params, progress)` to `handle_x(**kwargs)` with named parameters
- Return results instead of updating progress
- Keep all business logic (YouTube API calls, DB operations) identical
- Slow handlers (`handle_sync`, `handle_purge`) keep the `update` callback for BackgroundTasks compatibility

Key signature changes:
```python
# Fast handlers — direct call, return result
async def handle_create_playlist(title: str, description: str = "", privacy: str = "private") -> dict
async def handle_delete_playlist(playlist_id: str, db_path: str) -> dict
async def handle_add_videos(playlist_id: str, video_ids: list[str]) -> dict
async def handle_remove_video(playlist_id: str, video_id: str, db_path: str) -> dict
async def handle_reorder(playlist_id: str, video_ids: list[str], db_path: str) -> dict
async def handle_like(video_id: str) -> dict
async def handle_unlike(video_id: str) -> dict
async def handle_like_all(playlist_id: str, db_path: str) -> dict

# Slow handlers — take update callback for BackgroundTasks
async def handle_sync(update: Callable) -> dict
async def handle_export(target: str, threshold: float = 50.0) -> dict
async def handle_purge(update: Callable, threshold: float = 50.0, headless: bool = True) -> dict
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_handlers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/handlers.py tests/test_handlers.py
git commit -m "refactor: rewrite handlers as direct async functions"
```

---

### Task 3: Rewrite Playlist Routes to Direct Calls

Remove queue submission. Routes call handlers directly and return results.

**Files:**
- Modify: `src/youtube_helper/web/routes/playlists.py`
- Modify: `tests/test_web_playlists.py`

**Step 1: Write the failing tests**

Update route tests to expect 200 responses with results instead of 202 with operation_id.

```python
# In tests/test_web_playlists.py — update the create/delete/add/remove tests
# Example for create:
async def test_create_playlist(client):
    with patch("youtube_helper.web.routes.playlists.handle_create_playlist") as mock:
        mock.return_value = {"id": "PLnew", "title": "Test"}
        response = await client.post("/api/playlists", json={
            "title": "Test", "description": "", "privacy": "private"
        })
        assert response.status_code == 200  # was 202
        data = response.json()
        assert data["id"] == "PLnew"  # was operation_id
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_playlists.py -v`
Expected: FAIL — routes still return 202 with operation_id

**Step 3: Rewrite routes**

Update `src/youtube_helper/web/routes/playlists.py`:
- Remove `QueueManager` import and usage
- Import handlers directly: `from youtube_helper.web.handlers import handle_create_playlist, ...`
- Call handlers inline: `result = await handle_create_playlist(title=body.title, ...)`
- Return result with 200

```python
# Example route:
@router.post("/api/playlists")
async def create_playlist(body: CreatePlaylistRequest):
    result = await handle_create_playlist(
        title=body.title,
        description=body.description,
        privacy=body.privacy,
    )
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_playlists.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/routes/playlists.py tests/test_web_playlists.py
git commit -m "refactor: playlist routes call handlers directly, return 200"
```

---

### Task 4: Rewrite Sync Route with BackgroundTasks

Sync is a slow operation — use the BackgroundTasks pattern.

**Files:**
- Modify: `src/youtube_helper/web/routes/sync.py`
- Modify: `src/youtube_helper/web/app.py` (attach BackgroundTasks to app state)
- Create: `tests/test_web_sync.py`

**Step 1: Write the failing tests**

```python
# tests/test_web_sync.py
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from youtube_helper.web.app import create_app


@pytest.fixture
async def client(tmp_path):
    app = create_app()
    app.state.db_path = str(tmp_path / "test.db")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_sync_returns_202(client):
    with patch("youtube_helper.web.routes.sync.handle_sync", new_callable=AsyncMock):
        response = await client.post("/api/sync")
        assert response.status_code == 202
        assert response.json()["status"] == "running"


@pytest.mark.asyncio
async def test_sync_status_returns_state(client):
    response = await client.get("/api/sync/status")
    assert response.status_code == 200
    # No sync running, returns idle or null
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_sync.py -v`
Expected: FAIL — sync route still uses queue

**Step 3: Rewrite sync route and update app.py**

In `src/youtube_helper/web/app.py`:
- Remove QueueProcessor, EventBroadcaster, handler registration, processor startup
- Add `BackgroundTasks` instance to `app.state.bg_tasks`
- Remove BufferedSSEHandler log wiring

In `src/youtube_helper/web/routes/sync.py`:
```python
from fastapi import APIRouter, Request
from youtube_helper.web.handlers import handle_sync

router = APIRouter()

@router.post("/api/sync", status_code=202)
async def sync(request: Request):
    bg = request.app.state.bg_tasks
    bg.start("sync", handle_sync)
    return {"status": "running", "message": "Sync started"}

@router.get("/api/sync/status")
async def sync_status(request: Request):
    bg = request.app.state.bg_tasks
    status = bg.get_status("sync")
    if status is None:
        return {"status": "idle"}
    return status
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_sync.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/routes/sync.py src/youtube_helper/web/app.py tests/test_web_sync.py
git commit -m "refactor: sync uses BackgroundTasks instead of queue"
```

---

### Task 5: Add Google Takeout Parser

Parse Google Takeout Watch Later export files. Takeout exports a JSON file with video entries.

**Files:**
- Create: `src/youtube_helper/takeout.py`
- Test: `tests/test_takeout.py`

**Step 1: Write the failing tests**

```python
# tests/test_takeout.py
import json
import pytest
from youtube_helper.takeout import parse_takeout_watch_later


def test_parse_takeout_json():
    """Takeout exports playlist as JSON with video URLs."""
    takeout_data = json.dumps([
        {
            "contentDetails": {
                "videoId": "dQw4w9WgXcQ",
                "videoPublishedAt": "2009-10-25T06:57:33.000Z"
            },
            "snippet": {
                "title": "Rick Astley - Never Gonna Give You Up",
                "position": 0,
                "resourceId": {"videoId": "dQw4w9WgXcQ"}
            }
        },
        {
            "contentDetails": {
                "videoId": "abc123",
                "videoPublishedAt": "2020-01-01T00:00:00.000Z"
            },
            "snippet": {
                "title": "Another Video",
                "position": 1,
                "resourceId": {"videoId": "abc123"}
            }
        }
    ])
    result = parse_takeout_watch_later(takeout_data.encode())
    assert len(result) == 2
    assert result[0]["video_id"] == "dQw4w9WgXcQ"
    assert result[0]["title"] == "Rick Astley - Never Gonna Give You Up"
    assert result[1]["video_id"] == "abc123"


def test_parse_takeout_csv():
    """Takeout sometimes exports as CSV."""
    csv_data = b"Video Id,Time Added\ndQw4w9WgXcQ,2024-01-15 10:30:00 UTC\nabc123,2024-02-20 15:00:00 UTC\n"
    result = parse_takeout_watch_later(csv_data)
    assert len(result) == 2
    assert result[0]["video_id"] == "dQw4w9WgXcQ"
    assert result[1]["video_id"] == "abc123"


def test_parse_takeout_extracts_ids_from_urls():
    """Some Takeout formats include full URLs."""
    takeout_data = json.dumps([
        {
            "titleUrl": "https://www.youtube.com/watch?v\\u003ddQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up"
        }
    ])
    result = parse_takeout_watch_later(takeout_data.encode())
    assert len(result) == 1
    assert result[0]["video_id"] == "dQw4w9WgXcQ"


def test_parse_empty_file():
    result = parse_takeout_watch_later(b"[]")
    assert result == []


def test_parse_invalid_data():
    with pytest.raises(ValueError, match="Could not parse"):
        parse_takeout_watch_later(b"not valid data at all")
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_takeout.py -v`
Expected: FAIL — module not found

**Step 3: Write implementation**

```python
# src/youtube_helper/takeout.py
"""Parse Google Takeout Watch Later export files."""

import csv
import io
import json
import re


def parse_takeout_watch_later(data: bytes) -> list[dict]:
    """Parse a Takeout Watch Later export. Accepts JSON or CSV bytes.

    Returns list of dicts with at minimum: video_id, title (if available).
    """
    text = data.decode("utf-8").strip()

    # Try JSON first
    try:
        entries = json.loads(text)
        if isinstance(entries, list):
            return _parse_json_entries(entries)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try CSV
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if rows and ("Video Id" in rows[0] or "videoId" in rows[0]):
            return _parse_csv_rows(rows)
    except csv.Error:
        pass

    raise ValueError("Could not parse Takeout file as JSON or CSV")


def _parse_json_entries(entries: list[dict]) -> list[dict]:
    results = []
    for entry in entries:
        video_id = None
        title = entry.get("title", "")

        # Format 1: contentDetails.videoId or snippet.resourceId.videoId
        cd = entry.get("contentDetails", {})
        if "videoId" in cd:
            video_id = cd["videoId"]
        snippet = entry.get("snippet", {})
        rid = snippet.get("resourceId", {})
        if not video_id and "videoId" in rid:
            video_id = rid["videoId"]
        if not title and "title" in snippet:
            title = snippet["title"]

        # Format 2: titleUrl with encoded URL
        if not video_id and "titleUrl" in entry:
            match = re.search(r"v[=\u003d]([a-zA-Z0-9_-]{11})", entry["titleUrl"])
            if match:
                video_id = match.group(1)

        if video_id:
            results.append({"video_id": video_id, "title": title})
    return results


def _parse_csv_rows(rows: list[dict]) -> list[dict]:
    results = []
    for row in rows:
        video_id = row.get("Video Id") or row.get("videoId", "")
        video_id = video_id.strip()
        if video_id:
            results.append({"video_id": video_id, "title": row.get("Title", "")})
    return results
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_takeout.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/youtube_helper/takeout.py tests/test_takeout.py
git commit -m "feat: add Google Takeout Watch Later parser"
```

---

### Task 6: Add Watch Later Import Route

File upload endpoint that parses Takeout data and imports into DB.

**Files:**
- Modify: `src/youtube_helper/web/routes/watch_later.py`
- Modify: `tests/test_web_watch_later.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_web_watch_later.py
@pytest.mark.asyncio
async def test_import_watch_later(client):
    takeout_json = json.dumps([{
        "contentDetails": {"videoId": "dQw4w9WgXcQ"},
        "snippet": {"title": "Test Video", "resourceId": {"videoId": "dQw4w9WgXcQ"}}
    }]).encode()

    with patch("youtube_helper.web.routes.watch_later.parse_takeout_watch_later") as mock_parse:
        mock_parse.return_value = [{"video_id": "dQw4w9WgXcQ", "title": "Test Video"}]
        with patch("youtube_helper.web.routes.watch_later._import_videos") as mock_import:
            mock_import.return_value = 1
            response = await client.post(
                "/api/watch-later/import",
                files={"file": ("watch-later.json", takeout_json, "application/json")}
            )
            assert response.status_code == 200
            assert response.json()["imported"] == 1
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_watch_later.py::test_import_watch_later -v`
Expected: FAIL — endpoint doesn't exist

**Step 3: Add import endpoint**

Add to `src/youtube_helper/web/routes/watch_later.py`:
```python
from fastapi import UploadFile, File
from youtube_helper.takeout import parse_takeout_watch_later

@router.post("/api/watch-later/import")
async def import_watch_later(request: Request, file: UploadFile = File(...)):
    data = await file.read()
    videos = parse_takeout_watch_later(data)
    count = await _import_videos(videos, request.app.state.db_path)
    return {"imported": count, "total_parsed": len(videos)}
```

The `_import_videos` helper upserts videos into the DB:
- Creates WL playlist row if not exists (`id='WL'`, `title='Watch Later'`, `source='takeout'`)
- Upserts each video into `videos` table
- Upserts into `playlist_videos` junction table
- Optionally batch-fetches metadata via YouTube API for thumbnails/duration (if authenticated)
- Sets `watch_later_status = 'imported'` (new column or use existing fields)

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_watch_later.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/routes/watch_later.py tests/test_web_watch_later.py
git commit -m "feat: add Watch Later import from Google Takeout"
```

---

### Task 7: Rewrite Watch Later Export as Direct Request/Response

Export creates/finds a target playlist and adds all imported Watch Later videos via API. No queue.

**Files:**
- Modify: `src/youtube_helper/web/handlers.py` (rewrite handle_export)
- Modify: `src/youtube_helper/web/routes/watch_later.py`
- Modify: `tests/test_handlers.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_handlers.py
@pytest.mark.asyncio
async def test_handle_export_returns_counts(mock_settings):
    with patch("youtube_helper.web.handlers._get_youtube_client") as mock_yt:
        client = MagicMock()
        # Mock list_playlists to return existing target
        client.list_playlists.return_value = [
            {"id": "PLtarget", "snippet": {"title": "My Saved Videos"}}
        ]
        client.add_to_playlist.return_value = {"id": "item1"}
        mock_yt.return_value = client

        with patch("youtube_helper.web.handlers.get_connection") as mock_db:
            conn = MagicMock()
            conn.execute.return_value.fetchall.return_value = [
                {"video_id": "abc123"}, {"video_id": "def456"}
            ]
            mock_db.return_value.__enter__ = MagicMock(return_value=conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            result = await handle_export(target="My Saved Videos")
            assert result["exported"] == 2
            assert result["playlist_id"] == "PLtarget"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_handlers.py::test_handle_export_returns_counts -v`
Expected: FAIL — handle_export still has old signature

**Step 3: Rewrite handle_export**

- New signature: `async def handle_export(target: str, threshold: float = 50.0) -> dict`
- Returns `{"exported": count, "playlist_id": id, "playlist_title": title}`
- After adding each video, marks it as `exported` in local DB
- No progress callback

Update route in `watch_later.py`:
```python
@router.post("/api/watch-later/export")
async def export_watch_later(request: Request, body: ExportRequest):
    result = await handle_export(target=body.target, threshold=body.threshold)
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_handlers.py tests/test_web_watch_later.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/handlers.py src/youtube_helper/web/routes/watch_later.py tests/test_handlers.py
git commit -m "refactor: Watch Later export is direct request/response"
```

---

### Task 8: Simplify Playwright to Purge-Only

Strip the scraping code from browser/watch_later.py. Keep only the video removal logic and Chrome profile handling.

**Files:**
- Modify: `src/youtube_helper/browser/watch_later.py`
- Modify: `src/youtube_helper/web/routes/watch_later.py` (purge endpoint + status)
- Modify: `tests/test_watch_later.py`

**Step 1: Write the failing test**

```python
# tests/test_browser_purge.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from youtube_helper.browser.watch_later import purge_videos_from_watch_later


@pytest.mark.asyncio
async def test_purge_calls_remove_for_each_video():
    video_ids = ["abc123", "def456"]

    with patch("youtube_helper.browser.watch_later._launch_chrome") as mock_launch:
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_launch.return_value = (mock_context, None)

        with patch("youtube_helper.browser.watch_later._remove_video_from_page") as mock_remove:
            mock_remove.return_value = True

            results = await purge_videos_from_watch_later(
                video_ids=video_ids,
                update=lambda **kw: None,
            )
            assert results["removed"] == 2
            assert mock_remove.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_browser_purge.py -v`
Expected: FAIL — function doesn't exist yet

**Step 3: Rewrite browser/watch_later.py**

- Delete `scrape_watch_later()` function and all scraping/scrolling/extraction code
- Delete `parse_duration_text()`, `parse_progress_bar()` helpers (no longer needed)
- Keep: `find_chrome_profile_path()`, `_copy_chrome_profile()`, `_launch_chrome()` (profile handling)
- Add: `purge_videos_from_watch_later(video_ids, update, headless=True)` — the main entry point
- Keep: `_remove_video_from_page(page, video_id)` — extracted from old handle_purge logic
- Function signature: `async def purge_videos_from_watch_later(video_ids: list[str], update: Callable, headless: bool = True) -> dict`
- Returns: `{"removed": count, "skipped": count, "failed": count}`

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_browser_purge.py -v`
Expected: PASS

**Step 5: Wire up purge route with BackgroundTasks**

Update `src/youtube_helper/web/routes/watch_later.py`:
```python
@router.post("/api/watch-later/purge", status_code=202)
async def purge_watch_later(request: Request, body: PurgeRequest):
    bg = request.app.state.bg_tasks
    exported_ids = _get_exported_video_ids(request.app.state.db_path)

    async def job(update):
        await purge_videos_from_watch_later(
            video_ids=exported_ids, update=update, headless=body.headless
        )

    bg.start("purge", job)
    return {"status": "running", "message": "Purge started", "total": len(exported_ids)}

@router.get("/api/watch-later/purge/status")
async def purge_status(request: Request):
    bg = request.app.state.bg_tasks
    status = bg.get_status("purge")
    if status is None:
        return {"status": "idle"}
    return status
```

**Step 6: Commit**

```bash
git add src/youtube_helper/browser/watch_later.py src/youtube_helper/web/routes/watch_later.py tests/test_browser_purge.py
git commit -m "refactor: simplify Playwright to purge-only, add purge status endpoint"
```

---

### Task 9: Delete Queue Infrastructure

Remove all queue, SSE, and event broadcasting code.

**Files:**
- Delete: `src/youtube_helper/web/queue.py`
- Delete: `src/youtube_helper/web/processor.py`
- Delete: `src/youtube_helper/web/events.py`
- Delete: `src/youtube_helper/web/log_handler.py`
- Delete: `src/youtube_helper/web/routes/queue.py`
- Delete: `src/youtube_helper/web/routes/events.py`
- Delete: `src/youtube_helper/web/routes/logs.py`
- Delete: `migrations/002_operation_queue.sql`
- Delete: `tests/test_queue.py` (if exists)
- Delete: `tests/test_processor.py` (if exists)
- Modify: `src/youtube_helper/web/app.py` (remove all queue/event imports and wiring)
- Modify: `src/youtube_helper/web/routes/__init__.py` (remove queue/events/logs router imports)

**Step 1: Delete the files**

```bash
rm -f src/youtube_helper/web/queue.py
rm -f src/youtube_helper/web/processor.py
rm -f src/youtube_helper/web/events.py
rm -f src/youtube_helper/web/log_handler.py
rm -f src/youtube_helper/web/routes/queue.py
rm -f src/youtube_helper/web/routes/events.py
rm -f src/youtube_helper/web/routes/logs.py
rm -f migrations/002_operation_queue.sql
rm -f tests/test_queue.py
rm -f tests/test_processor.py
```

**Step 2: Clean up app.py imports and wiring**

Remove from `src/youtube_helper/web/app.py`:
- `QueueProcessor` import and initialization
- `EventBroadcaster` import and initialization
- `BufferedSSEHandler` import and log wiring
- `register_all_handlers()` call
- Processor task creation in lifespan
- `app.state.broadcaster`, `app.state.queue_processor`
- Router includes for queue, events, logs

Add: `app.state.bg_tasks = BackgroundTasks()`

**Step 3: Run all backend tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/ -v`
Expected: PASS (no import errors, no references to deleted modules)

**Step 4: Fix any remaining references**

Search for any remaining imports of deleted modules and fix them.

Run: `grep -r "from youtube_helper.web.queue\|from youtube_helper.web.processor\|from youtube_helper.web.events\|from youtube_helper.web.log_handler" src/ tests/`

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: delete queue, processor, SSE, and event broadcasting infrastructure"
```

---

### Task 10: Update Frontend API Client

Remove queue/SSE methods, add import and status polling methods.

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/__tests__/client.test.ts`

**Step 1: Write the failing test**

```typescript
// Add to frontend/src/api/__tests__/client.test.ts
describe('watch later import', () => {
  it('uploads file to import endpoint', async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ imported: 5 }));
    const file = new File(['[]'], 'watch-later.json', { type: 'application/json' });
    const result = await api.importWatchLater(file);
    expect(result.imported).toBe(5);
  });
});

describe('sync status', () => {
  it('fetches sync status', async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ status: 'running', progress: 50 }));
    const result = await api.syncStatus();
    expect(result.status).toBe('running');
  });
});

describe('purge status', () => {
  it('fetches purge status', async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ status: 'idle' }));
    const result = await api.purgeStatus();
    expect(result.status).toBe('idle');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/api/__tests__/client.test.ts`
Expected: FAIL — methods don't exist

**Step 3: Update client.ts**

Remove from `api` object:
- `listQueue`, `cancelOp`, `retryOp`, `skipOp`, `clearQueue`
- `getLogs`, `clearLogs`
- `scrapeWatchLater`, `pruneExports`
- `QueueOp` and `LogEntry` types

Add to `api` object:
```typescript
importWatchLater: async (file: File) => {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/api/watch-later/import`, {
    method: 'POST',
    body: form,
  });
  return res.json();
},
syncStatus: async () => {
  const res = await fetch(`${BASE}/api/sync/status`);
  return res.json();
},
purgeStatus: async () => {
  const res = await fetch(`${BASE}/api/watch-later/purge/status`);
  return res.json();
},
```

Update existing methods that returned `{operation_id}` — they now return actual results.

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/api/__tests__/client.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/__tests__/client.test.ts
git commit -m "refactor: update API client — remove queue methods, add import/status"
```

---

### Task 11: Update Frontend Hooks

Remove queue/SSE hooks. Simplify mutations. Add polling for slow ops.

**Files:**
- Modify: `frontend/src/hooks/useApi.ts`
- Delete: `frontend/src/hooks/useSSE.ts`
- Delete: `frontend/src/hooks/__tests__/useSSE.test.ts`
- Modify: `frontend/src/hooks/__tests__/useApi.test.tsx`

**Step 1: Write the failing test**

```typescript
// Update frontend/src/hooks/__tests__/useApi.test.tsx
describe('useSync', () => {
  it('posts to sync endpoint and invalidates queries on success', async () => {
    // Test that mutation calls api.sync() and invalidates playlists
  });
});

describe('useSyncStatus', () => {
  it('polls sync status while running', async () => {
    // Test refetchInterval behavior
  });
});

describe('useImportWatchLater', () => {
  it('uploads file and invalidates watch-later queries', async () => {
    // Test file upload mutation
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/hooks/__tests__/useApi.test.tsx`
Expected: FAIL

**Step 3: Rewrite hooks**

Remove from `useApi.ts`:
- `useQueue()` — no more queue polling
- `useScrape()` — no more scraping
- `usePruneExports()` — removed feature
- `useClearQueue()`, `useClearLogs()`, `useLogs()`
- All `queryClient.invalidateQueries({ queryKey: ['queue'] })` calls

Add to `useApi.ts`:
```typescript
export function useSyncStatus() {
  return useQuery({
    queryKey: ['sync-status'],
    queryFn: () => api.syncStatus(),
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? 2000 : false,
  });
}

export function usePurgeStatus() {
  return useQuery({
    queryKey: ['purge-status'],
    queryFn: () => api.purgeStatus(),
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? 2000 : false,
  });
}

export function useImportWatchLater() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.importWatchLater(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watch-later'] }),
  });
}
```

Update existing mutations:
- `useSync()` — `onSuccess` invalidates `['sync-status']` to trigger polling
- `useExportWL()` — no longer invalidates queue, just invalidates `['watch-later']`
- `usePurgeWL()` — `onSuccess` invalidates `['purge-status']` to trigger polling

**Step 4: Delete SSE files**

```bash
rm -f frontend/src/hooks/useSSE.ts
rm -f frontend/src/hooks/__tests__/useSSE.test.ts
```

**Step 5: Run tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run`
Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove SSE/queue hooks, add status polling and import hook"
```

---

### Task 12: Update Layout and Remove Queue/Log Panels

Remove QueuePanel, LogPanel, and SSE wiring from Layout.

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Delete: `frontend/src/components/QueuePanel.tsx`
- Delete: `frontend/src/components/LogPanel.tsx`
- Delete: `frontend/src/components/__tests__/QueuePanel.test.tsx`
- Modify: `frontend/src/components/__tests__/Layout.test.tsx`

**Step 1: Write the failing test**

```typescript
// Update frontend/src/components/__tests__/Layout.test.tsx
// Remove tests for queue badge, queue panel toggle, SSE event handling
// Add test that layout renders without queue/log panels
it('renders navigation without queue panel', () => {
  render(<Layout />);
  expect(screen.queryByText('Queue')).not.toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/components/__tests__/Layout.test.tsx`
Expected: FAIL — QueuePanel still imported

**Step 3: Update Layout.tsx**

- Remove imports: `QueuePanel`, `LogPanel`, `useSSE`, `useQueue`
- Remove state: `queueOpen`, `logOpen`
- Remove SSE event handler and `useSSE()` call
- Remove queue badge from AppBar
- Remove QueuePanel and LogPanel drawer components
- Keep: navigation, sidebar, routing (Outlet), responsive drawer

**Step 4: Delete panel components**

```bash
rm -f frontend/src/components/QueuePanel.tsx
rm -f frontend/src/components/LogPanel.tsx
rm -f frontend/src/components/__tests__/QueuePanel.test.tsx
```

**Step 5: Run tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run`
Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove QueuePanel, LogPanel, and SSE from Layout"
```

---

### Task 13: Update Video Routes (Like/Unlike)

Convert like/unlike from queue to direct calls.

**Files:**
- Modify: `src/youtube_helper/web/routes/videos.py`
- Modify: `tests/test_web_videos.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_like_video_returns_200(client):
    with patch("youtube_helper.web.routes.videos.handle_like") as mock:
        mock.return_value = {"video_id": "abc123", "status": "liked"}
        response = await client.post("/api/videos/abc123/like")
        assert response.status_code == 200
        assert response.json()["status"] == "liked"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_videos.py -v`
Expected: FAIL — still returns 202

**Step 3: Rewrite video routes**

```python
from youtube_helper.web.handlers import handle_like, handle_unlike

@router.post("/api/videos/{video_id}/like")
async def like_video(video_id: str):
    result = await handle_like(video_id=video_id)
    return result

@router.post("/api/videos/{video_id}/unlike")
async def unlike_video(video_id: str):
    result = await handle_unlike(video_id=video_id)
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/test_web_videos.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/youtube_helper/web/routes/videos.py tests/test_web_videos.py
git commit -m "refactor: like/unlike routes call handlers directly"
```

---

### Task 14: Remove Scrape CLI Command, Update Watch Later CLI

Update CLI to reflect new flow (import instead of scrape).

**Files:**
- Modify: `src/youtube_helper/cli/watch_later.py`

**Step 1: Update CLI commands**

- Remove `scrape` subcommand
- Add `import` subcommand that accepts a file path
- Keep `export`, `purge` commands but update to call new handler signatures
- Remove `prune-exports` subcommand

**Step 2: Run CLI help to verify**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m youtube_helper.cli.watch_later --help`
Expected: Shows `import`, `export`, `purge`, `show-watched`, `show-unwatched`

**Step 3: Commit**

```bash
git add src/youtube_helper/cli/watch_later.py
git commit -m "refactor: update Watch Later CLI — import replaces scrape"
```

---

### Task 15: Final Cleanup and Full Test Run

Verify everything works end-to-end.

**Step 1: Search for stale references**

```bash
grep -r "QueueManager\|QueueProcessor\|EventBroadcaster\|operation_queue\|useSSE\|QueuePanel\|LogPanel\|scrape_watch_later" src/ frontend/src/ tests/ --include="*.py" --include="*.ts" --include="*.tsx"
```

Fix any remaining references found.

**Step 2: Run all backend tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Run all frontend tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run`
Expected: ALL PASS

**Step 4: Start the app and verify it loads**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && python -m youtube_helper.cli.web --port 8000`
Verify: App starts without import errors, health check at `/health` returns 200

**Step 5: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final cleanup after queue removal"
```
