# YouTube Helper — Design Document

**Date:** 2026-03-02
**Status:** Draft

## Overview

A personal Python CLI + web dashboard tool for managing YouTube private playlists at scale (50+ playlists, thousands of videos), with download capabilities and history ingestion. Built for a single user's channel management workflow.

## Tech Stack

### Backend / CLI
- **Python 3.11+** — Runtime
- **Click** — CLI command framework
- **Rich** — Beautiful terminal output (tables, progress bars, panels, syntax highlighting)
- **Textual** — Interactive TUI mode
- **google-api-python-client + google-auth-oauthlib** — YouTube Data API v3
- **yt-dlp** — Video downloading
- **ffmpeg** (subprocess) — Post-processing
- **SQLite** — Local metadata cache and history store
- **thefuzz** — Fuzzy string matching
- **FastAPI** — Web API backend

### Frontend (Web Dashboard)
- **React** (Vite) — SPA frontend
- **Material UI (MUI)** — Component library and styling
- **React Router** — Navigation
- **React Query (TanStack Query)** — Server state management

## Architecture

```
youtube-helper/
├── src/youtube_helper/
│   ├── cli/              # Click commands
│   │   ├── __init__.py
│   │   ├── main.py       # CLI entrypoint
│   │   ├── auth.py       # yt auth setup/status
│   │   ├── sync.py       # yt sync
│   │   ├── playlist.py   # yt playlist *
│   │   ├── search.py     # yt search
│   │   ├── download.py   # yt download
│   │   ├── history.py    # yt history *
│   │   └── analyze.py    # yt analyze (noop stub)
│   ├── tui/              # Textual interactive mode
│   │   ├── __init__.py
│   │   └── app.py        # yt browse
│   ├── api/              # YouTube API client
│   │   ├── __init__.py
│   │   ├── client.py     # API wrapper
│   │   ├── playlists.py  # Playlist operations
│   │   └── videos.py     # Video metadata
│   ├── cache/            # SQLite layer
│   │   ├── __init__.py
│   │   ├── db.py         # Database setup/migrations
│   │   ├── models.py     # Data models
│   │   └── queries.py    # Query helpers
│   ├── download/         # yt-dlp wrapper
│   │   ├── __init__.py
│   │   └── downloader.py
│   ├── history/          # History ingestion
│   │   ├── __init__.py
│   │   ├── takeout.py    # Google Takeout parser
│   │   └── liked.py      # Liked videos importer
│   ├── search/           # Fuzzy search engine
│   │   ├── __init__.py
│   │   └── fuzzy.py
│   ├── web/              # FastAPI web backend
│   │   ├── __init__.py
│   │   ├── app.py        # FastAPI app
│   │   └── routes/       # API routes
│   ├── analyze/          # Content intelligence (noop)
│   │   ├── __init__.py
│   │   └── stub.py       # Placeholder for future transcription/parsing
│   └── config/           # Auth, settings
│       ├── __init__.py
│       └── settings.py
├── frontend/             # React web dashboard
│   ├── src/
│   │   ├── components/   # MUI-based components
│   │   ├── pages/        # Route pages
│   │   ├── hooks/        # React Query hooks
│   │   ├── api/          # API client
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── tests/
├── docs/
│   └── plans/
└── pyproject.toml
```

## SQLite Schema (Core Tables)

```sql
-- Playlists
CREATE TABLE playlists (
    id TEXT PRIMARY KEY,          -- YouTube playlist ID
    title TEXT NOT NULL,
    description TEXT,
    privacy_status TEXT,          -- public/private/unlisted
    video_count INTEGER,
    last_synced TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Videos
CREATE TABLE videos (
    id TEXT PRIMARY KEY,          -- YouTube video ID
    title TEXT NOT NULL,
    channel_id TEXT,
    channel_name TEXT,
    description TEXT,
    duration INTEGER,             -- seconds
    published_at TIMESTAMP,
    thumbnail_url TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    last_synced TIMESTAMP
);

-- Playlist-Video relationship
CREATE TABLE playlist_videos (
    playlist_id TEXT REFERENCES playlists(id),
    video_id TEXT REFERENCES videos(id),
    position INTEGER,
    added_at TIMESTAMP,
    PRIMARY KEY (playlist_id, video_id)
);

-- Watch history (from Google Takeout)
CREATE TABLE watch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT,
    title TEXT,                   -- stored separately in case video is deleted
    channel_name TEXT,
    watched_at TIMESTAMP,
    source TEXT DEFAULT 'takeout' -- takeout or api
);

-- Liked videos
CREATE TABLE liked_videos (
    video_id TEXT PRIMARY KEY REFERENCES videos(id),
    liked_at TIMESTAMP
);

-- Download tracking
CREATE TABLE downloads (
    video_id TEXT REFERENCES videos(id),
    playlist_id TEXT REFERENCES playlists(id),
    file_path TEXT,
    quality TEXT,
    downloaded_at TIMESTAMP,
    file_size INTEGER,
    PRIMARY KEY (video_id, playlist_id)
);
```

## Features by Phase

### Phase 1: Auth, Sync, Playlist Management, Fuzzy Search, Rich Output

**Auth:**
- `yt auth setup` — Guided walkthrough:
  1. Check for existing Google Cloud project with YouTube Data API
  2. If none found, step-by-step instructions to create one
  3. OAuth consent screen setup guidance
  4. OAuth 2.0 credential creation
  5. Run OAuth flow, store refresh token locally
- `yt auth status` — Show current auth state, token expiry, quota usage

**Sync:**
- `yt sync` — Pull all playlist and video metadata into SQLite
  - First run: full sync (may take a while with 1000s of videos)
  - Subsequent runs: incremental sync (only fetch changes)
  - Rich progress: animated spinner per playlist, overall progress bar
- Sync is metadata-only — never downloads video files automatically

**Playlist Management:**
- `yt playlist list` — Rich table of all playlists
- `yt playlist show <name>` — Videos in a playlist (fuzzy matched name)
- `yt playlist move <video> --from <playlist> --to <playlist>`
- `yt playlist copy <video> --to <playlist>`
- `yt playlist remove <video> --from <playlist>`
- `yt playlist dedupe [playlist|--all]` — Find and remove duplicates
- `yt playlist cleanup` — Find deleted/unavailable videos across all playlists
- `yt playlist export <playlist> --format csv|json`
- Bulk operations via `--filter` flag: `--filter "channel:Name"`, `--filter "duration:<10m"`

**Fuzzy Search:**
- `yt search <query>` — Fuzzy search across all video titles, channel names, playlist names
- `yt search --playlists-only` / `--videos-only` — Scoped search
- All commands that accept playlist/video names use fuzzy matching
- Multiple matches show ranked selection prompt
- Powered by thefuzz against local SQLite cache

**Rich Terminal Output:**
- Color-coded tables with alternating rows
- Bordered status panels for auth/sync state
- Animated spinners and progress bars with ETA
- Highlighted search matches
- Diff-style before/after for move/remove operations
- Styled confirmation prompts for destructive actions

### Phase 2: History Ingester

**Google Takeout Watch History:**
- `yt history import --watch <path>` — Parse Takeout HTML or JSON
- Handles both export formats
- Deduplicates against existing data on re-import

**Liked Videos:**
- `yt history import --liked` — Pull via YouTube API
- `yt history import --all <path>` — Both at once

**Cross-referencing:**
- `yt history check <playlist>` — Which videos have you watched / not watched
- `yt history stats` — Most watched channels, total watch time, patterns
- Unified search spans playlists + watch history + liked videos
- Results tagged with source

### Phase 3: Interactive TUI (`yt browse`)

- Built with Textual
- Sidebar: collapsible playlist tree with video counts
- Main panel: video list for selected playlist
- Fuzzy search bar (/) filters in real-time
- Keyboard shortcuts: m=move, c=copy, d=delete, s=search, q=quit
- Multi-select with checkboxes for bulk operations
- Bottom status bar: sync state, selection count, key hints
- Searches across playlists, history, and liked videos

### Phase 4: Web Dashboard (`yt web`)

- `yt web` — Starts FastAPI server and opens browser
- FastAPI backend exposes REST API over the same SQLite data
- React + MUI frontend:
  - **Dashboard home** — Playlist overview cards with video counts, quick stats
  - **Playlist browser** — Click into playlists, sortable/filterable video tables
  - **Search** — Real-time fuzzy search across everything
  - **Playlist management** — Drag-and-drop reordering, bulk select, move/copy/delete
  - **History view** — Watch history timeline, liked videos grid
  - **Download manager** — Select videos to download, monitor progress
  - **Settings** — Auth status, sync controls, download preferences

### Phase 5: Downloads

- `yt download <video>` — Single video download
- `yt download --playlist <playlist>` — Full playlist
- `yt download --playlist <playlist> --new` — Only new additions
- `yt download --filter "duration:<10m" --playlist <playlist>`
- Quality presets: `--quality best|1080p|720p|audio-only`
- Configurable output: naming templates (`{channel}/{title}.{ext}`), per-playlist folders
- Download tracking in SQLite (no re-downloads)
- Resume interrupted downloads
- Rich progress: per-file bar with speed/ETA, overall progress, completion summary

### Phase 6: Content Intelligence (Noop Stub)

- `yt analyze <video>` — Placeholder command, prints "Content analysis coming soon"
- Architecture accounts for future:
  - Download video → extract audio → transcribe (Whisper) → parse/summarize
  - Searchable transcripts in SQLite
  - Topic extraction, key moments
  - Integration with search (search within video content)
- Stubbed out so the module structure and CLI entry points exist

## Auth & Setup Guide

The tool will include a built-in setup wizard (`yt auth setup`) that walks through:

1. **Check for existing project:**
   - Look for existing credentials in `~/.youtube-helper/`
   - Prompt user to check console.cloud.google.com for existing projects

2. **Create Google Cloud project (if needed):**
   - Direct link to console.cloud.google.com/projectcreate
   - Step-by-step: name project, enable YouTube Data API v3
   - Navigate to APIs & Services > Credentials
   - Create OAuth 2.0 Client ID (Desktop application)
   - Download client_secret.json

3. **Configure the tool:**
   - `yt auth setup --client-secret <path-to-json>`
   - Runs OAuth flow in browser
   - Stores refresh token in `~/.youtube-helper/credentials.json`

4. **Verify:**
   - `yt auth status` confirms working auth and shows channel info

## Configuration

Stored in `~/.youtube-helper/config.toml`:

```toml
[general]
cache_dir = "~/.youtube-helper/cache"
download_dir = "~/Videos/YouTube"

[download]
quality = "best"
naming = "{channel}/{title}.{ext}"
```

## Design Principles

- **Metadata by default, files opt-in** — Sync only pulls metadata. Downloading video files is always an explicit user action.
- **Offline-first browsing** — SQLite cache means you can browse, search, and plan operations without internet. API calls happen on sync and mutations.
- **Beautiful output** — Every command should look good in the terminal. Rich tables, progress bars, and panels throughout.
- **Fuzzy everything** — Never make the user remember exact names or copy-paste IDs.
- **Non-destructive** — Confirmation prompts before any YouTube-side changes. Dry-run support for bulk operations.
