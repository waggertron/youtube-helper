# Simplify App: Remove Queue, Rework Watch Later

**Date**: 2026-03-17
**Status**: Approved

## Motivation

The queue system was added prematurely — it adds ~20 files of infrastructure (SQLite-backed queue, SSE broadcasting, progress tracking, retry/cancel/skip) for operations that are mostly fast API calls. The Watch Later browser automation (Playwright scraping) was designed but never confirmed working. Time to simplify both.

## Core Design Decisions

1. **Remove the queue system entirely** — replace with direct request/response for fast ops, simple `asyncio.Task` + polling for slow ops
2. **Replace Watch Later scraping with Google Takeout import** — reliable, no browser automation needed for reading data
3. **Keep Playwright only for Watch Later purge** — the one operation that absolutely requires browser automation (removing videos from Watch Later)

## Watch Later Flow

### Step 1: Import from Google Takeout

- User downloads Watch Later from Google Takeout (JSON/CSV)
- `POST /api/watch-later/import` accepts file upload
- Parses file, extracts video IDs
- Batch-fetches metadata via YouTube API (`get_video_details`)
- Upserts into `videos` + `playlist_videos` (playlist_id='WL')
- Returns import count

### Step 2: Export to Custom Playlist via API

- `POST /api/watch-later/export` — direct request/response
- Creates or uses existing target playlist via YouTube API
- Adds all Watch Later videos in batches of 50
- Marks each video as `exported` in local DB once confirmed added
- Returns result with counts

### Step 3: Purge from Watch Later via Playwright

- `POST /api/watch-later/purge` kicks off `asyncio.Task`, returns 202
- `GET /api/watch-later/purge/status` returns `{status, removed, total, current_video}`
- Launches Playwright with Chrome profile (keep existing profile-copy logic)
- Navigates to Watch Later, scrolls to load videos
- For each exported video: find by video ID, click menu, click "Remove"
- Marks each as `purged` in local DB
- Skips videos not found on page (already removed)
- Re-triggerable: only attempts videos not yet marked `purged`

### Video Status Tracking

Each Watch Later video progresses through: `imported → exported → purged`

## Non-Watch-Later Operations

### Fast Operations — Direct Request/Response (200)

- `create_playlist` — single API call
- `delete_playlist` — single API call
- `add_videos` — batch API calls
- `remove_video` — single API call
- `like_video` / `unlike_video` — single API call
- `reorder_playlist` — local DB only

### Slow Operations — asyncio.Task + Polling (202)

- **Sync**: `POST /api/sync` → 202, poll `GET /api/sync/status`
- **Purge**: `POST /api/watch-later/purge` → 202, poll `GET /api/watch-later/purge/status`

Both use the same pattern: store task state in app-level dict, poll status endpoint every 2-3 seconds.

## Files to Delete

- `src/youtube_helper/web/queue.py` — QueueManager
- `src/youtube_helper/web/processor.py` — QueueProcessor
- `src/youtube_helper/web/routes/queue.py` — Queue API endpoints
- `src/youtube_helper/web/events.py` — EventBroadcaster
- `src/youtube_helper/web/routes/events.py` — SSE endpoint
- `src/youtube_helper/web/log_handler.py` — SSE log handler
- `src/youtube_helper/web/routes/logs.py` — Log streaming routes
- `frontend/src/components/QueuePanel.tsx` — Queue panel UI
- `frontend/src/components/LogPanel.tsx` — Log panel UI
- `frontend/src/hooks/useSSE.ts` — SSE hook
- `migrations/002_operation_queue.sql` — Queue table
- Related test files for queue, processor, SSE

## Files to Modify

- `src/youtube_helper/web/handlers.py` — Rewrite from queue handlers to direct async functions
- `src/youtube_helper/web/app.py` — Remove processor startup, handler registration
- `src/youtube_helper/web/routes/playlists.py` — Direct handler calls, return 200
- `src/youtube_helper/web/routes/watch_later.py` — New import endpoint, simplified export/purge
- `src/youtube_helper/web/routes/sync.py` — asyncio.Task pattern
- `frontend/src/hooks/useApi.ts` — Remove queue hooks, simplify mutations
- `frontend/src/components/Layout.tsx` — Remove SSE wiring
- `frontend/src/api/client.ts` — Remove queue API methods, add import/status methods

## Files to Add

- Takeout parser module (for parsing Google Takeout JSON/CSV)
- Background task manager (lightweight: dict of task states, ~30 lines)

## Files to Simplify

- `src/youtube_helper/browser/watch_later.py` — Remove scraping code, keep only the Playwright launch + remove-video interaction
