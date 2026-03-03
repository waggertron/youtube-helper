# Web Dashboard — Design Document

**Date:** 2026-03-03
**Status:** Draft

## Overview

A web dashboard for youtube-helper that provides a visual interface for all existing CLI functionality. FastAPI backend wraps existing Python modules (no logic duplication). React + MUI frontend communicates via REST and SSE for real-time progress on long-running operations.

## Architecture

```
src/youtube_helper/web/       # FastAPI backend
  app.py                      # FastAPI app, static file serving, CORS
  routes/
    playlists.py              # Playlist CRUD + reorder
    videos.py                 # Video details, like/unlike
    watch_later.py            # WL scrape, export, purge, prune
    search.py                 # Fuzzy search
    sync.py                   # Trigger sync
    auth.py                   # Auth status
    events.py                 # SSE endpoint

frontend/                     # React + Vite + MUI
  src/
    components/               # Shared components (VideoTable, ProgressBar, ConfirmDialog)
    pages/                    # Route pages
      Dashboard.tsx
      Playlists.tsx
      PlaylistDetail.tsx
      WatchLater.tsx
      Search.tsx
      LikedVideos.tsx
      Settings.tsx
    hooks/                    # useSSE, React Query hooks
    api/                      # API client (fetch wrappers)
    App.tsx                   # Router + MUI theme + layout
  vite.config.ts
  package.json
```

## Running

- **Development:** `make dev` — runs uvicorn (port 8000, --reload) and vite dev server (port 5173, proxy to API) concurrently
- **Production:** `yt web` — builds frontend, serves from FastAPI as static files, opens browser to localhost:8000
- **Build only:** `make build-ui`

## Operation Queue

All API-consuming and long-running operations go through a sequential queue rather than firing immediately. This manages quota usage and prevents conflicts.

**How it works:**
- Actions (move videos, export, sync, scrape, purge, like, etc.) are submitted to a queue
- One operation executes at a time, in submission order
- Each operation reports progress via SSE
- On failure, the queue pauses and surfaces the error — user can retry or skip
- Queue state persists in SQLite so it survives server restarts

**API:**
- `GET /api/queue` — List all queued operations (pending, active, completed, failed)
- `POST /api/queue` — Submit an operation to the queue
- `DELETE /api/queue/{id}` — Cancel a pending operation
- `POST /api/queue/{id}/retry` — Retry a failed operation
- `POST /api/queue/{id}/skip` — Skip a failed operation and continue

**Frontend:**
- Queue panel visible in the sidebar or as a collapsible bottom drawer
- Shows: current operation with progress, pending count, completed count
- Failed operations highlighted in red with retry/skip buttons
- Quota usage indicator alongside the queue (estimated cost of pending operations)

**Backend:**
- `src/youtube_helper/web/queue.py` — Queue manager (asyncio task that processes items sequentially)
- Queue items stored in a `operation_queue` SQLite table: id, type, params (JSON), status, progress, created_at, started_at, completed_at, error

## API Endpoints

### Playlists
- `GET /api/playlists` — List all playlists
- `POST /api/playlists` — Create a playlist
- `DELETE /api/playlists/{id}` — Delete a playlist
- `GET /api/playlists/{id}/videos` — Videos in a playlist with watch progress
- `POST /api/playlists/{id}/videos` — Add videos to a playlist
- `DELETE /api/playlists/{id}/videos/{video_id}` — Remove video from playlist
- `PUT /api/playlists/{id}/reorder` — Reorder videos (accepts ordered list of video IDs)

### Videos
- `POST /api/videos/{id}/like` — Like a video
- `DELETE /api/videos/{id}/like` — Unlike a video
- `GET /api/videos/liked` — List liked videos

### Watch Later
- `GET /api/watch-later` — All Watch Later videos
- `GET /api/watch-later/watched?threshold=50` — Videos watched above threshold
- `GET /api/watch-later/unwatched?threshold=50` — Unwatched videos
- `POST /api/watch-later/scrape` — Trigger Playwright scrape (SSE progress)
- `POST /api/watch-later/export` — Full export workflow (SSE progress)
- `POST /api/watch-later/purge` — Playwright purge of watched videos (SSE progress)
- `POST /api/watch-later/prune-exports` — Remove watched from export playlists

### Search
- `GET /api/search?q=` — Fuzzy search across videos and playlists

### Sync
- `POST /api/sync` — Trigger YouTube API sync (SSE progress)

### Auth
- `GET /api/auth/status` — Current authentication state

### Events
- `GET /api/events` — SSE endpoint for all operation progress

## Frontend Pages

### 1. Dashboard
- Overview cards: playlist count, total videos, Watch Later count, last sync time
- Quick action buttons: Sync, Scrape Watch Later
- Recent activity feed

### 2. Playlists
- Grid/list of all playlists with video counts, privacy badges, thumbnails
- Click into playlist to see sortable/filterable video table
- Actions: create, delete, reorder
- Per-video actions: move, copy, remove, like/unlike

### 3. Watch Later
- Watch Later videos with watch progress bars
- Filter by watched/unwatched with adjustable threshold slider
- Action buttons: Scrape, Export, Purge, Prune Exports
- Real-time progress panel during operations (via SSE)

### 4. Search
- Search bar with instant fuzzy results
- Results grouped by type (videos, playlists)
- Click result to navigate to playlist or video detail

### 5. Liked Videos
- Grid/list of liked videos
- Like/unlike toggle available on any video across the app

### 6. Settings
- Auth status display
- Sync controls
- Default export target playlist name
- Default watched threshold

## Navigation
- Persistent sidebar (MUI Drawer) with icons for each page
- Top bar with sync status indicator and global search shortcut

## Real-Time Updates (SSE)
- Long-running operations (sync, scrape, purge, export) run in asyncio background tasks
- Progress events pushed via SSE to a broadcast channel
- Frontend subscribes with a custom `useSSE` hook on operation start
- Auto-reconnect with exponential backoff on connection drop
- "Reconnecting" banner shown during disconnection

## Error Handling & UX
- **Confirmation dialogs** (MUI Dialog) for destructive actions: delete playlist, purge Watch Later, remove videos
- **Toast notifications** (MUI Snackbar) for operation success/failure and quota warnings
- **Auth guard** — Unauthenticated state shows panel directing user to `yt auth setup` in CLI
- **Quota awareness** — Display remaining API quota in settings, warn before bulk operations
- **Optimistic UI** — Like/unlike and remove operations update UI immediately, roll back on failure
- **Loading states** — MUI Skeleton components while data loads, disabled buttons during in-flight operations

## Dependencies

### Backend (added to pyproject.toml)
- `fastapi`
- `uvicorn`
- `sse-starlette`

### Frontend (package.json)
- `react`, `react-dom`
- `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled`
- `react-router-dom`
- `@tanstack/react-query`
- `vite`, `typescript`

## Future Features

### Drag-and-Drop Playlist Management
- Drag videos between playlists
- Drag to reorder within a playlist
- Visual drop targets with hover feedback
- Would use `@dnd-kit/core` or similar library
- Builds on top of the button-based move/copy/reorder already in place
