# youtube-helper

A personal CLI tool for managing YouTube playlists at scale. Built for power users with 50+ playlists and thousands of videos, where YouTube's UI falls apart.

Uses the **YouTube Data API v3** for playlist management, **Playwright** for Watch Later automation (since Google deprecated the API for it), and a local **SQLite** cache so you can browse and search offline.

## Features

- **Sync** all your YouTube playlists and video metadata into a local database
- **Scrape Watch Later** via browser automation, including watch progress detection from thumbnail progress bars
- **Export Watch Later** to dated private playlists with a master archive
- **Purge watched videos** from Watch Later (configurable threshold)
- **Fuzzy search** across all videos and playlists by title, channel, or name
- **Rich terminal output** with color-coded tables, progress bars, and styled panels
- **Prune export playlists** by removing videos you've already watched

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/waggertron/youtube-helper.git
cd youtube-helper
uv venv
uv pip install -e ".[dev]"
playwright install chromium
```

## Setup

### 1. Initialize the database

```bash
yt db init
```

### 2. Set up YouTube API access

```bash
yt auth setup
```

This walks you through:

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable **YouTube Data API v3** (APIs & Services > Library)
4. Create OAuth credentials (APIs & Services > Credentials > OAuth Client ID > Desktop app)
5. Download the client secret JSON file
6. Configure the OAuth consent screen and add yourself as a test user

The CLI will prompt you for the path to your `client_secret.json` and run the OAuth flow.

### 3. Verify authentication

```bash
yt auth status
```

## Usage

### Sync playlists from YouTube

Pull all playlist and video metadata into your local database:

```bash
yt sync
```

This fetches metadata only (no video files). Uses the local SQLite cache so subsequent commands work offline.

### Watch Later management

YouTube's Watch Later playlist is not accessible via the API (deprecated since 2016). This tool uses Playwright with your existing Chrome profile to automate it.

**Scrape Watch Later into the database:**

```bash
yt wl scrape
```

Launches Chrome (using your logged-in profile), scrolls through your Watch Later, and extracts video metadata plus watch progress from the thumbnail progress bars.

**See what you've watched:**

```bash
yt wl show-watched              # Videos watched >= 50%
yt wl show-watched -t 75        # Videos watched >= 75%
```

**See what's unwatched:**

```bash
yt wl show-unwatched
```

**Export Watch Later (the full workflow):**

```bash
yt wl export --target "spacepope videos"
```

This does everything in one command:

1. Creates a private playlist `Watch Later Export 2026-03-02` with all current Watch Later videos
2. Appends all videos to the `Watch Later Archive` master playlist (append-only)
3. Copies unwatched videos to your target playlist (default: "spacepope videos")
4. Removes watched videos from the local database

Use `--dry-run` to preview without making changes. Use `--threshold` to adjust what counts as "watched" (default: 50%).

**Remove watched videos from Watch Later via browser:**

```bash
yt wl purge                     # Remove videos watched >= 50%
yt wl purge -t 75               # Remove videos watched >= 75%
yt wl purge --dry-run           # Preview what would be removed
```

**Prune export playlists:**

Remove already-watched videos from previously created export playlists:

```bash
yt wl prune-exports
```

### Search

Fuzzy search across all videos and playlists:

```bash
yt search "python tutorial"
yt search "python" --videos-only
yt search "favorites" --playlists-only
yt search "react" -t 80         # Higher match threshold
```

### Browse playlists

```bash
yt playlist list                # Show all synced playlists
yt playlist show favorites      # Fuzzy-matched, shows videos with progress bars
yt playlist show "prog tut"     # Partial match works too
```

### Content analysis (coming soon)

```bash
yt analyze <video>              # Placeholder for future transcription/summarization
```

## CLI Reference

```
yt [OPTIONS] COMMAND [ARGS]

Commands:
  analyze   Analyze video content (coming soon)
  auth      Authentication and API setup
    setup     Set up YouTube API authentication
    status    Show current authentication status
  db        Database management commands
    init      Initialize the database and run migrations
    status    Show current migration status
  playlist  Playlist browsing and management
    list      List all synced playlists
    show      Show videos in a playlist (fuzzy matched)
  search    Fuzzy search across all videos and playlists
  sync      Sync all playlist metadata from YouTube
  wl        Watch Later playlist management
    scrape          Scrape Watch Later via Playwright
    show-watched    Show videos watched above threshold
    show-unwatched  Show unwatched videos
    export          Export Watch Later to dated playlist
    purge           Remove watched videos via browser
    prune-exports   Remove watched from export playlists

Options:
  --version      Show version
  -v, --verbose  Enable verbose output
  --help         Show help
```

## Architecture

```
src/youtube_helper/
  cli/            Click CLI commands
  api/            YouTube Data API v3 client (OAuth, playlists, videos)
  browser/        Playwright automation for Watch Later
  watch_later/    Watch Later management logic
  sync/           Sync engine (API -> SQLite)
  search/         Fuzzy search (thefuzz)
  analyze/        Content intelligence (stub)
  config/         Settings and paths
  db/             SQLite connection and migrations
```

**Two-track approach:**
- **YouTube API** for regular playlists (list, create, add, remove, sync)
- **Playwright** for Watch Later (scrape, purge) since Google deprecated API access

All data flows through a local **SQLite** database with WAL mode for performance. The database acts as a cache so you can search and browse without hitting the API.

## API Quota Notes

YouTube Data API has a daily quota of 10,000 units (default):

| Operation | Cost |
|---|---|
| List playlists/videos | 1 unit/page |
| Add video to playlist | 50 units |
| Remove video from playlist | 50 units |
| Create playlist | 50 units |

Moving 100 videos = ~10,000 units (at limit). For bulk operations with thousands of videos, request a quota increase from Google Cloud Console or batch across days.

Watch Later operations use Playwright (zero API quota).

## Configuration

Config and data stored in `~/.youtube-helper/`:

```
~/.youtube-helper/
  youtube-helper.db       SQLite database
  client_secret.json      Google OAuth client secret
  token.pickle            OAuth refresh token
```

## Development

```bash
uv venv
uv pip install -e ".[dev]"
pytest -v                       # Run tests (65 tests)
ruff check                      # Lint
```

## Tech Stack

- Python 3.11+
- Click (CLI framework)
- Rich (terminal output)
- SQLite (local cache)
- google-api-python-client (YouTube API)
- Playwright (browser automation)
- thefuzz (fuzzy matching)
- pytest (testing)

## License

MIT
