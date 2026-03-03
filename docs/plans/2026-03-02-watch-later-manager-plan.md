# Watch Later Manager — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core youtube-helper CLI that can sync playlist metadata into SQLite, automate Watch Later operations via Playwright (using existing Chrome profile), manage regular playlists via the YouTube API, and provide beautiful Rich terminal output.

**Architecture:** Two-track approach — Playwright browser automation for Watch Later (since the API deprecated it), YouTube Data API v3 for all other playlists. Both feed into a shared SQLite cache. CLI built with Click, output with Rich.

**Tech Stack:** Python 3.11+, Click, Rich, SQLite, google-api-python-client, google-auth-oauthlib, Playwright, thefuzz, pytest

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/youtube_helper/__init__.py`
- Create: `src/youtube_helper/cli/__init__.py`
- Create: `src/youtube_helper/cli/main.py`
- Create: `.gitignore`
- Create: `migrations/`
- Test: `tests/conftest.py`
- Test: `tests/test_cli.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "youtube-helper"
version = "0.1.0"
description = "Personal CLI tool for managing YouTube playlists and content"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "thefuzz[speedup]>=0.22",
    "google-api-python-client>=2.100",
    "google-auth-oauthlib>=1.0",
    "google-auth-httplib2>=0.2",
    "playwright>=1.40",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.4",
]

[project.scripts]
yt = "youtube_helper.cli.main:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests requiring auth",
]

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

**Step 2: Create .gitignore**

```gitignore
__pycache__/
*.py[cod]
*$py.class
dist/
build/
*.egg-info/
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/
.DS_Store
*.db
token.pickle
credentials.json
client_secret*.json
```

**Step 3: Create src/youtube_helper/__init__.py**

```python
"""YouTube Helper — personal CLI for managing YouTube content."""
```

**Step 4: Create src/youtube_helper/cli/__init__.py**

```python
```

**Step 5: Create src/youtube_helper/cli/main.py**

```python
import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """yt — YouTube Helper CLI for managing playlists and content."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
```

**Step 6: Create tests/conftest.py**

```python
import sqlite3

import pytest
from click.testing import CliRunner

from youtube_helper.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_invoke(runner):
    def invoke(*args, **kwargs):
        return runner.invoke(cli, args, catch_exceptions=False, **kwargs)
    return invoke
```

**Step 7: Write the failing test — tests/test_cli.py**

```python
def test_cli_help(cli_invoke):
    result = cli_invoke("--help")
    assert result.exit_code == 0
    assert "YouTube Helper" in result.output


def test_cli_version(cli_invoke):
    result = cli_invoke("--version")
    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

**Step 8: Install and run tests**

Run:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_cli.py -v
```
Expected: PASS

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with Click CLI entrypoint"
```

---

### Task 2: SQLite Database & Migration System

**Files:**
- Create: `src/youtube_helper/db/__init__.py`
- Create: `src/youtube_helper/db/connection.py`
- Create: `src/youtube_helper/db/migrations.py`
- Create: `migrations/001_initial_schema.sql`
- Create: `src/youtube_helper/cli/db.py`
- Test: `tests/test_db.py`

**Step 1: Write failing tests — tests/test_db.py**

```python
import sqlite3
from pathlib import Path

import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import get_current_version, run_migrations


class TestConnection:
    def test_get_connection_returns_connection(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_connection_has_wal_mode(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_connection_has_foreign_keys(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        conn.close()

    def test_connection_has_row_factory(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestMigrations:
    def test_fresh_db_has_version_zero(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        assert get_current_version(db_path) == 0

    def test_run_migrations_applies_initial(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        applied = run_migrations(db_path)
        assert len(applied) > 0
        assert 1 in applied

    def test_migrations_are_idempotent(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        first_run = run_migrations(db_path)
        second_run = run_migrations(db_path)
        assert len(first_run) > 0
        assert len(second_run) == 0

    def test_version_increments_after_migration(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        assert get_current_version(db_path) >= 1

    def test_initial_schema_creates_tables(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        conn = get_connection(db_path)
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        assert "playlists" in tables
        assert "videos" in tables
        assert "playlist_videos" in tables
        assert "watch_history" in tables
        assert "liked_videos" in tables
        assert "downloads" in tables
        conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db.py -v`
Expected: FAIL (modules don't exist)

**Step 3: Create src/youtube_helper/db/__init__.py**

```python
```

**Step 4: Create src/youtube_helper/db/connection.py**

```python
import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn
```

**Step 5: Create src/youtube_helper/db/migrations.py**

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

from youtube_helper.db.connection import get_connection

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "migrations"


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_versions (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def get_current_version(db_path: str) -> int:
    conn = get_connection(db_path)
    _ensure_version_table(conn)
    row = conn.execute("SELECT MAX(version) FROM _schema_versions").fetchone()
    version = row[0] or 0
    conn.close()
    return version


def _discover_migrations() -> list[tuple[int, str, Path]]:
    migrations = []
    if not MIGRATIONS_DIR.exists():
        return migrations
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        parts = sql_file.stem.split("_", 1)
        version = int(parts[0])
        name = parts[1] if len(parts) > 1 else sql_file.stem
        migrations.append((version, name, sql_file))
    return migrations


def run_migrations(db_path: str) -> list[int]:
    conn = get_connection(db_path)
    _ensure_version_table(conn)

    current = conn.execute("SELECT MAX(version) FROM _schema_versions").fetchone()[0] or 0
    applied = []

    for version, name, path in _discover_migrations():
        if version <= current:
            continue
        sql = path.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO _schema_versions (version, name) VALUES (?, ?)",
            (version, name),
        )
        conn.commit()
        applied.append(version)

    conn.close()
    return applied
```

**Step 6: Create migrations/001_initial_schema.sql**

```sql
CREATE TABLE playlists (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    privacy_status TEXT DEFAULT 'private',
    video_count INTEGER DEFAULT 0,
    source TEXT DEFAULT 'api',
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT (datetime('now')),
    updated_at TIMESTAMP DEFAULT (datetime('now'))
);

CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    channel_id TEXT DEFAULT '',
    channel_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    duration INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    thumbnail_url TEXT DEFAULT '',
    is_available BOOLEAN DEFAULT 1,
    watch_progress REAL DEFAULT 0.0,
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT (datetime('now'))
);

CREATE TABLE playlist_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id TEXT NOT NULL REFERENCES playlists(id),
    video_id TEXT NOT NULL REFERENCES videos(id),
    playlist_item_id TEXT DEFAULT '',
    position INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT (datetime('now')),
    UNIQUE(playlist_id, video_id)
);

CREATE TABLE watch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT DEFAULT '',
    title TEXT DEFAULT '',
    channel_name TEXT DEFAULT '',
    watched_at TIMESTAMP,
    source TEXT DEFAULT 'takeout'
);

CREATE TABLE liked_videos (
    video_id TEXT PRIMARY KEY,
    liked_at TIMESTAMP
);

CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL REFERENCES videos(id),
    playlist_id TEXT REFERENCES playlists(id),
    file_path TEXT DEFAULT '',
    quality TEXT DEFAULT '',
    downloaded_at TIMESTAMP DEFAULT (datetime('now')),
    file_size INTEGER DEFAULT 0
);

CREATE INDEX idx_videos_channel ON videos(channel_name);
CREATE INDEX idx_playlist_videos_playlist ON playlist_videos(playlist_id);
CREATE INDEX idx_playlist_videos_video ON playlist_videos(video_id);
CREATE INDEX idx_watch_history_video ON watch_history(video_id);
CREATE INDEX idx_watch_history_watched ON watch_history(watched_at);
```

**Step 7: Run tests to verify they pass**

Run: `pytest tests/test_db.py -v`
Expected: ALL PASS

**Step 8: Add `yt db` CLI commands — src/youtube_helper/cli/db.py**

```python
import click
from rich.console import Console
from rich.panel import Panel

from youtube_helper.db.migrations import get_current_version, run_migrations

console = Console()


@click.group()
def db() -> None:
    """Database management commands."""
    pass


@db.command()
@click.option(
    "--db-path",
    default="~/.youtube-helper/youtube-helper.db",
    help="Path to SQLite database.",
)
def init(db_path: str) -> None:
    """Initialize the database and run all migrations."""
    import os
    from pathlib import Path

    db_path = str(Path(db_path).expanduser())
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    applied = run_migrations(db_path)

    if applied:
        console.print(
            Panel(
                f"[green]Database initialized at [bold]{db_path}[/bold]\n"
                f"Applied {len(applied)} migration(s): {applied}[/green]",
                title="[bold]Database Ready[/bold]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[cyan]Database at [bold]{db_path}[/bold] is already up to date.[/cyan]",
                title="[bold]Database Status[/bold]",
                border_style="cyan",
            )
        )


@db.command()
@click.option(
    "--db-path",
    default="~/.youtube-helper/youtube-helper.db",
    help="Path to SQLite database.",
)
def status(db_path: str) -> None:
    """Show current migration status."""
    from pathlib import Path

    db_path = str(Path(db_path).expanduser())
    version = get_current_version(db_path)
    console.print(
        Panel(
            f"[cyan]Schema version:[/cyan] [bold]{version}[/bold]",
            title="[bold]Database Status[/bold]",
            border_style="cyan",
        )
    )
```

**Step 9: Register db command in main.py**

Update `src/youtube_helper/cli/main.py` — add at the bottom:

```python
from youtube_helper.cli.db import db
cli.add_command(db)
```

**Step 10: Test db CLI commands**

Add to `tests/test_cli.py`:

```python
def test_db_init(runner, tmp_path):
    from youtube_helper.cli.main import cli

    db_path = str(tmp_path / "test.db")
    result = runner.invoke(cli, ["db", "init", "--db-path", db_path])
    assert result.exit_code == 0
    assert "Database" in result.output


def test_db_status(runner, tmp_path):
    from youtube_helper.cli.main import cli

    db_path = str(tmp_path / "test.db")
    runner.invoke(cli, ["db", "init", "--db-path", db_path])
    result = runner.invoke(cli, ["db", "status", "--db-path", db_path])
    assert result.exit_code == 0
```

**Step 11: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 12: Commit**

```bash
git add -A
git commit -m "feat: SQLite database with migration system and db CLI commands"
```

---

### Task 3: YouTube API Authentication

**Files:**
- Create: `src/youtube_helper/config/__init__.py`
- Create: `src/youtube_helper/config/settings.py`
- Create: `src/youtube_helper/api/__init__.py`
- Create: `src/youtube_helper/api/auth.py`
- Create: `src/youtube_helper/cli/auth.py`
- Test: `tests/test_auth.py`

**Step 1: Write failing tests — tests/test_auth.py**

```python
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from youtube_helper.config.settings import Settings


class TestSettings:
    def test_default_config_dir(self):
        settings = Settings()
        assert ".youtube-helper" in str(settings.config_dir)

    def test_custom_config_dir(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert settings.config_dir == tmp_path

    def test_db_path(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert str(settings.db_path).endswith("youtube-helper.db")

    def test_credentials_path(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert str(settings.credentials_path).endswith("credentials.json")

    def test_client_secret_path(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert str(settings.client_secret_path).endswith("client_secret.json")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/config/__init__.py**

```python
```

**Step 4: Create src/youtube_helper/config/settings.py**

```python
from __future__ import annotations

from pathlib import Path


class Settings:
    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".youtube-helper"

    @property
    def db_path(self) -> Path:
        return self.config_dir / "youtube-helper.db"

    @property
    def credentials_path(self) -> Path:
        return self.config_dir / "credentials.json"

    @property
    def client_secret_path(self) -> Path:
        return self.config_dir / "client_secret.json"

    @property
    def token_path(self) -> Path:
        return self.config_dir / "token.pickle"

    def ensure_dirs(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_auth.py -v`
Expected: ALL PASS

**Step 6: Create src/youtube_helper/api/__init__.py**

```python
```

**Step 7: Create src/youtube_helper/api/auth.py**

```python
from __future__ import annotations

import pickle
from pathlib import Path

from youtube_helper.config.settings import Settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_authenticated_service(settings: Settings):
    """Build and return an authenticated YouTube API service."""
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials = None

    if settings.token_path.exists():
        with open(settings.token_path, "rb") as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not settings.client_secret_path.exists():
                raise FileNotFoundError(
                    f"Client secret not found at {settings.client_secret_path}. "
                    "Run 'yt auth setup' first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(settings.client_secret_path),
                scopes=SCOPES,
            )
            credentials = flow.run_local_server(
                port=8080,
                access_type="offline",
                prompt="consent",
            )

        settings.ensure_dirs()
        with open(settings.token_path, "wb") as token:
            pickle.dump(credentials, token)

    return build("youtube", "v3", credentials=credentials)
```

**Step 8: Create src/youtube_helper/cli/auth.py**

```python
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from youtube_helper.config.settings import Settings

console = Console()


@click.group()
def auth() -> None:
    """Authentication and API setup."""
    pass


@auth.command()
def setup() -> None:
    """Set up YouTube API authentication."""
    settings = Settings()

    console.print()
    console.print(
        Panel(
            "[bold cyan]YouTube API Setup Guide[/bold cyan]\n\n"
            "Follow these steps to configure API access:\n\n"
            "[bold]1.[/bold] Go to [link=https://console.cloud.google.com]console.cloud.google.com[/link]\n"
            "[bold]2.[/bold] Create a new project (or select existing)\n"
            "[bold]3.[/bold] Enable [bold]YouTube Data API v3[/bold]\n"
            "   → APIs & Services → Library → search 'YouTube Data API v3'\n"
            "[bold]4.[/bold] Create OAuth credentials\n"
            "   → APIs & Services → Credentials → Create Credentials → OAuth Client ID\n"
            "   → Application type: [bold]Desktop app[/bold]\n"
            "[bold]5.[/bold] Download the JSON file\n"
            "[bold]6.[/bold] Configure OAuth consent screen\n"
            "   → Add yourself as a test user\n"
            "   → Add scope: youtube.com/auth/youtube",
            title="[bold]Setup Instructions[/bold]",
            border_style="cyan",
        )
    )

    client_secret = click.prompt(
        "\nPath to your client_secret JSON file",
        type=click.Path(exists=True),
    )

    import shutil

    settings.ensure_dirs()
    shutil.copy2(client_secret, settings.client_secret_path)
    console.print(f"\n[green]✓ Client secret saved to {settings.client_secret_path}[/green]")

    console.print("\n[cyan]Starting OAuth flow — a browser window will open...[/cyan]\n")

    from youtube_helper.api.auth import get_authenticated_service

    try:
        youtube = get_authenticated_service(settings)
        channel = youtube.channels().list(part="snippet", mine=True).execute()
        if channel["items"]:
            name = channel["items"][0]["snippet"]["title"]
            console.print(
                Panel(
                    f"[green]Authenticated as [bold]{name}[/bold][/green]",
                    title="[bold]Success[/bold]",
                    border_style="green",
                )
            )
        else:
            console.print("[green]✓ Authentication successful[/green]")
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")


@auth.command()
def status() -> None:
    """Show current authentication status."""
    settings = Settings()

    table = Table(title="Authentication Status", border_style="cyan")
    table.add_column("Item", style="bold")
    table.add_column("Status")

    has_secret = settings.client_secret_path.exists()
    has_token = settings.token_path.exists()

    table.add_row(
        "Client Secret",
        "[green]Found[/green]" if has_secret else "[red]Missing[/red]",
    )
    table.add_row(
        "Auth Token",
        "[green]Found[/green]" if has_token else "[red]Missing[/red]",
    )
    table.add_row(
        "Config Dir",
        str(settings.config_dir),
    )

    console.print()
    console.print(table)

    if has_token:
        try:
            from youtube_helper.api.auth import get_authenticated_service

            youtube = get_authenticated_service(settings)
            channel = youtube.channels().list(part="snippet", mine=True).execute()
            if channel["items"]:
                name = channel["items"][0]["snippet"]["title"]
                console.print(f"\n[green]Authenticated as [bold]{name}[/bold][/green]")
        except Exception as e:
            console.print(f"\n[yellow]Token exists but may be expired: {e}[/yellow]")
```

**Step 9: Register auth command in main.py**

Add to `src/youtube_helper/cli/main.py`:

```python
from youtube_helper.cli.auth import auth
cli.add_command(auth)
```

**Step 10: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: YouTube API authentication with setup wizard and settings"
```

---

### Task 4: YouTube API Playlist Client

**Files:**
- Create: `src/youtube_helper/api/playlists.py`
- Create: `src/youtube_helper/api/videos.py`
- Test: `tests/test_api_playlists.py`

**Step 1: Write failing tests — tests/test_api_playlists.py**

```python
from unittest.mock import MagicMock, patch

import pytest

from youtube_helper.api.playlists import PlaylistClient


@pytest.fixture
def mock_youtube():
    return MagicMock()


@pytest.fixture
def client(mock_youtube):
    return PlaylistClient(mock_youtube)


class TestListPlaylists:
    def test_returns_playlists(self, client, mock_youtube):
        mock_youtube.playlists().list().execute.return_value = {
            "items": [
                {
                    "id": "PL123",
                    "snippet": {"title": "Test Playlist", "description": "desc"},
                    "status": {"privacyStatus": "private"},
                    "contentDetails": {"itemCount": 5},
                }
            ],
            "nextPageToken": None,
        }
        mock_youtube.playlists().list_next.return_value = None

        playlists = client.list_playlists()
        assert len(playlists) == 1
        assert playlists[0]["id"] == "PL123"


class TestListPlaylistItems:
    def test_returns_items(self, client, mock_youtube):
        mock_youtube.playlistItems().list().execute.return_value = {
            "items": [
                {
                    "id": "PLI123",
                    "snippet": {
                        "title": "Video 1",
                        "position": 0,
                        "resourceId": {"videoId": "VID1"},
                        "videoOwnerChannelTitle": "Channel 1",
                        "videoOwnerChannelId": "CH1",
                    },
                    "contentDetails": {"videoId": "VID1"},
                }
            ],
        }
        mock_youtube.playlistItems().list_next.return_value = None

        items = client.list_playlist_items("PL123")
        assert len(items) == 1
        assert items[0]["snippet"]["title"] == "Video 1"


class TestAddToPlaylist:
    def test_inserts_item(self, client, mock_youtube):
        mock_youtube.playlistItems().insert().execute.return_value = {"id": "PLI456"}
        result = client.add_to_playlist("PL123", "VID1")
        assert result["id"] == "PLI456"


class TestRemoveFromPlaylist:
    def test_deletes_item(self, client, mock_youtube):
        mock_youtube.playlistItems().delete().execute.return_value = ""
        client.remove_from_playlist("PLI123")
        mock_youtube.playlistItems().delete.assert_called()


class TestCreatePlaylist:
    def test_creates_private_playlist(self, client, mock_youtube):
        mock_youtube.playlists().insert().execute.return_value = {
            "id": "PL_NEW",
            "snippet": {"title": "New Playlist"},
        }
        result = client.create_playlist("New Playlist", privacy="private")
        assert result["id"] == "PL_NEW"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_playlists.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/api/playlists.py**

```python
from __future__ import annotations

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class PlaylistClient:
    def __init__(self, youtube):
        self.youtube = youtube

    def list_playlists(self) -> list[dict]:
        playlists = []
        request = self.youtube.playlists().list(
            part="snippet,status,contentDetails",
            mine=True,
            maxResults=50,
        )
        while request:
            response = request.execute()
            playlists.extend(response.get("items", []))
            request = self.youtube.playlists().list_next(request, response)
        return playlists

    def list_playlist_items(self, playlist_id: str) -> list[dict]:
        items = []
        request = self.youtube.playlistItems().list(
            part="snippet,contentDetails,status",
            playlistId=playlist_id,
            maxResults=50,
        )
        while request:
            response = request.execute()
            items.extend(response.get("items", []))
            request = self.youtube.playlistItems().list_next(request, response)
        return items

    def add_to_playlist(self, playlist_id: str, video_id: str, position: int | None = None) -> dict:
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        }
        if position is not None:
            body["snippet"]["position"] = position
        return self.youtube.playlistItems().insert(
            part="snippet",
            body=body,
        ).execute()

    def remove_from_playlist(self, playlist_item_id: str) -> None:
        self.youtube.playlistItems().delete(id=playlist_item_id).execute()

    def create_playlist(
        self,
        title: str,
        description: str = "",
        privacy: str = "private",
    ) -> dict:
        return self.youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                },
                "status": {
                    "privacyStatus": privacy,
                },
            },
        ).execute()
```

**Step 4: Create src/youtube_helper/api/videos.py**

```python
from __future__ import annotations


class VideoClient:
    def __init__(self, youtube):
        self.youtube = youtube

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """Get detailed info for up to 50 videos at a time."""
        videos = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            response = self.youtube.videos().list(
                part="snippet,contentDetails,status",
                id=",".join(chunk),
            ).execute()
            videos.extend(response.get("items", []))
        return videos
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_api_playlists.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: YouTube API playlist and video clients"
```

---

### Task 5: Sync Engine — Pull Playlists & Videos into SQLite

**Files:**
- Create: `src/youtube_helper/sync/__init__.py`
- Create: `src/youtube_helper/sync/engine.py`
- Create: `src/youtube_helper/cli/sync.py`
- Test: `tests/test_sync.py`

**Step 1: Write failing tests — tests/test_sync.py**

```python
import sqlite3
from unittest.mock import MagicMock

import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.sync.engine import SyncEngine


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def mock_playlist_client():
    client = MagicMock()
    client.list_playlists.return_value = [
        {
            "id": "PL123",
            "snippet": {"title": "My Playlist", "description": "Test"},
            "status": {"privacyStatus": "private"},
            "contentDetails": {"itemCount": 2},
        }
    ]
    client.list_playlist_items.return_value = [
        {
            "id": "PLI1",
            "snippet": {
                "title": "Video One",
                "position": 0,
                "resourceId": {"videoId": "VID1"},
                "videoOwnerChannelTitle": "Channel A",
                "videoOwnerChannelId": "CHA",
            },
            "contentDetails": {"videoId": "VID1", "videoPublishedAt": "2024-01-01T00:00:00Z"},
        },
        {
            "id": "PLI2",
            "snippet": {
                "title": "Video Two",
                "position": 1,
                "resourceId": {"videoId": "VID2"},
                "videoOwnerChannelTitle": "Channel B",
                "videoOwnerChannelId": "CHB",
            },
            "contentDetails": {"videoId": "VID2", "videoPublishedAt": "2024-02-01T00:00:00Z"},
        },
    ]
    return client


@pytest.fixture
def sync_engine(db_path, mock_playlist_client):
    return SyncEngine(db_path, mock_playlist_client)


class TestSyncPlaylists:
    def test_syncs_playlists_to_db(self, sync_engine, db_path):
        sync_engine.sync_all()
        conn = get_connection(db_path)
        playlists = conn.execute("SELECT * FROM playlists").fetchall()
        assert len(playlists) == 1
        assert playlists[0]["id"] == "PL123"
        assert playlists[0]["title"] == "My Playlist"
        conn.close()

    def test_syncs_videos_to_db(self, sync_engine, db_path):
        sync_engine.sync_all()
        conn = get_connection(db_path)
        videos = conn.execute("SELECT * FROM videos").fetchall()
        assert len(videos) == 2
        conn.close()

    def test_syncs_playlist_video_relationships(self, sync_engine, db_path):
        sync_engine.sync_all()
        conn = get_connection(db_path)
        rels = conn.execute("SELECT * FROM playlist_videos").fetchall()
        assert len(rels) == 2
        assert rels[0]["playlist_id"] == "PL123"
        conn.close()

    def test_sync_is_idempotent(self, sync_engine, db_path):
        sync_engine.sync_all()
        sync_engine.sync_all()
        conn = get_connection(db_path)
        videos = conn.execute("SELECT * FROM videos").fetchall()
        assert len(videos) == 2
        conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sync.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/sync/__init__.py**

```python
```

**Step 4: Create src/youtube_helper/sync/engine.py**

```python
from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

from youtube_helper.api.playlists import PlaylistClient
from youtube_helper.db.connection import get_connection

console = Console()


class SyncEngine:
    def __init__(self, db_path: str, playlist_client: PlaylistClient):
        self.db_path = db_path
        self.client = playlist_client

    def sync_all(self, verbose: bool = False) -> dict:
        stats = {"playlists": 0, "videos": 0, "relationships": 0}
        conn = get_connection(self.db_path)
        now = datetime.now(timezone.utc).isoformat()

        playlists = self.client.list_playlists()
        stats["playlists"] = len(playlists)

        for pl in playlists:
            conn.execute(
                """INSERT INTO playlists (id, title, description, privacy_status, video_count, source, last_synced)
                   VALUES (?, ?, ?, ?, ?, 'api', ?)
                   ON CONFLICT(id) DO UPDATE SET
                       title=excluded.title,
                       description=excluded.description,
                       privacy_status=excluded.privacy_status,
                       video_count=excluded.video_count,
                       last_synced=excluded.last_synced,
                       updated_at=datetime('now')""",
                (
                    pl["id"],
                    pl["snippet"]["title"],
                    pl["snippet"].get("description", ""),
                    pl["status"]["privacyStatus"],
                    pl["contentDetails"]["itemCount"],
                    now,
                ),
            )
            conn.commit()

            items = self.client.list_playlist_items(pl["id"])

            for item in items:
                video_id = item["snippet"]["resourceId"]["videoId"]
                title = item["snippet"].get("title", "")
                channel_name = item["snippet"].get("videoOwnerChannelTitle", "")
                channel_id = item["snippet"].get("videoOwnerChannelId", "")
                published = item["contentDetails"].get("videoPublishedAt", "")
                playlist_item_id = item["id"]
                position = item["snippet"].get("position", 0)

                conn.execute(
                    """INSERT INTO videos (id, title, channel_id, channel_name, published_at, last_synced)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           title=excluded.title,
                           channel_id=excluded.channel_id,
                           channel_name=excluded.channel_name,
                           published_at=excluded.published_at,
                           last_synced=excluded.last_synced""",
                    (video_id, title, channel_id, channel_name, published, now),
                )

                conn.execute(
                    """INSERT INTO playlist_videos (playlist_id, video_id, playlist_item_id, position)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(playlist_id, video_id) DO UPDATE SET
                           playlist_item_id=excluded.playlist_item_id,
                           position=excluded.position""",
                    (pl["id"], video_id, playlist_item_id, position),
                )
                conn.commit()

                stats["videos"] += 1
                stats["relationships"] += 1

        conn.close()
        return stats
```

**Step 5: Create src/youtube_helper/cli/sync.py**

```python
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

from youtube_helper.config.settings import Settings

console = Console()


@click.command()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Sync all playlist metadata from YouTube into local database."""
    settings = Settings()
    settings.ensure_dirs()

    from youtube_helper.api.auth import get_authenticated_service
    from youtube_helper.api.playlists import PlaylistClient
    from youtube_helper.db.migrations import run_migrations
    from youtube_helper.sync.engine import SyncEngine

    run_migrations(str(settings.db_path))

    with console.status("[bold cyan]Connecting to YouTube...[/bold cyan]", spinner="dots"):
        youtube = get_authenticated_service(settings)
        client = PlaylistClient(youtube)

    engine = SyncEngine(str(settings.db_path), client)

    console.print("\n[bold cyan]Syncing playlists and videos...[/bold cyan]\n")
    stats = engine.sync_all(verbose=ctx.obj.get("verbose", False))

    console.print(
        Panel(
            f"[green]Synced [bold]{stats['playlists']}[/bold] playlists, "
            f"[bold]{stats['videos']}[/bold] videos[/green]",
            title="[bold]Sync Complete[/bold]",
            border_style="green",
        )
    )
```

**Step 6: Register sync command in main.py**

Add to `src/youtube_helper/cli/main.py`:

```python
from youtube_helper.cli.sync import sync
cli.add_command(sync)
```

**Step 7: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add -A
git commit -m "feat: sync engine to pull YouTube playlists and videos into SQLite"
```

---

### Task 6: Playwright Watch Later Scraper

**Files:**
- Create: `src/youtube_helper/browser/__init__.py`
- Create: `src/youtube_helper/browser/watch_later.py`
- Create: `src/youtube_helper/cli/watch_later.py`
- Test: `tests/test_watch_later.py`

**Step 1: Write failing tests — tests/test_watch_later.py**

These test the data parsing logic, not the browser automation itself (which requires integration tests).

```python
import pytest

from youtube_helper.browser.watch_later import parse_video_entry, parse_progress_bar


class TestParseVideoEntry:
    def test_parses_valid_entry(self):
        entry = {
            "video_id": "abc123",
            "title": "Test Video",
            "channel": "Test Channel",
            "duration_text": "10:30",
            "progress_percent": 75.0,
            "thumbnail_url": "https://i.ytimg.com/vi/abc123/default.jpg",
        }
        result = parse_video_entry(entry)
        assert result["video_id"] == "abc123"
        assert result["title"] == "Test Video"
        assert result["duration_seconds"] == 630
        assert result["progress_percent"] == 75.0

    def test_parses_hours_duration(self):
        entry = {
            "video_id": "xyz",
            "title": "Long Video",
            "channel": "Ch",
            "duration_text": "1:30:00",
            "progress_percent": 0.0,
            "thumbnail_url": "",
        }
        result = parse_video_entry(entry)
        assert result["duration_seconds"] == 5400

    def test_handles_missing_duration(self):
        entry = {
            "video_id": "xyz",
            "title": "Live",
            "channel": "Ch",
            "duration_text": "",
            "progress_percent": 0.0,
            "thumbnail_url": "",
        }
        result = parse_video_entry(entry)
        assert result["duration_seconds"] == 0


class TestParseProgressBar:
    def test_parses_percentage_from_width(self):
        assert parse_progress_bar("width: 75%") == 75.0

    def test_zero_for_no_progress(self):
        assert parse_progress_bar("") == 0.0

    def test_handles_decimal(self):
        assert parse_progress_bar("width: 33.5%") == 33.5
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_watch_later.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/browser/__init__.py**

```python
```

**Step 4: Create src/youtube_helper/browser/watch_later.py**

```python
from __future__ import annotations

import re
import time

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

console = Console()


def parse_duration_text(text: str) -> int:
    """Convert duration string like '10:30' or '1:30:00' to seconds."""
    if not text or not text.strip():
        return 0
    parts = text.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
    except ValueError:
        return 0
    return 0


def parse_progress_bar(style_attr: str) -> float:
    """Extract percentage from a style attribute like 'width: 75%'."""
    if not style_attr:
        return 0.0
    match = re.search(r"width:\s*([\d.]+)%", style_attr)
    if match:
        return float(match.group(1))
    return 0.0


def parse_video_entry(entry: dict) -> dict:
    """Normalize a scraped video entry."""
    return {
        "video_id": entry["video_id"],
        "title": entry["title"],
        "channel": entry["channel"],
        "duration_seconds": parse_duration_text(entry.get("duration_text", "")),
        "progress_percent": entry.get("progress_percent", 0.0),
        "thumbnail_url": entry.get("thumbnail_url", ""),
    }


def find_chrome_profile_path() -> str:
    """Find the default Chrome user data directory on macOS."""
    from pathlib import Path

    mac_path = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    if mac_path.exists():
        return str(mac_path)
    raise FileNotFoundError(
        "Chrome profile not found. Expected at: " + str(mac_path)
    )


async def scrape_watch_later(
    max_videos: int = 5000,
    headless: bool = False,
) -> list[dict]:
    """Scrape the Watch Later playlist using Playwright with Chrome profile."""
    from playwright.async_api import async_playwright

    chrome_path = find_chrome_profile_path()

    videos = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        console.print("[cyan]Navigating to Watch Later...[/cyan]")
        await page.goto("https://www.youtube.com/playlist?list=WL", wait_until="networkidle")

        # Wait for playlist content to load
        await page.wait_for_selector("ytd-playlist-video-renderer", timeout=15000)

        # Scroll to load all videos
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 100

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} videos"),
        ) as progress:
            task = progress.add_task("Scrolling to load videos...", total=max_videos)

            while scroll_attempts < max_scroll_attempts:
                renderers = await page.query_selector_all("ytd-playlist-video-renderer")
                current_count = len(renderers)
                progress.update(task, completed=current_count)

                if current_count >= max_videos:
                    break
                if current_count == last_count:
                    scroll_attempts += 1
                    if scroll_attempts > 5:
                        break
                else:
                    scroll_attempts = 0

                last_count = current_count
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(800)

        # Extract video data
        renderers = await page.query_selector_all("ytd-playlist-video-renderer")

        console.print(f"[cyan]Extracting data from {len(renderers)} videos...[/cyan]")

        for renderer in renderers:
            try:
                # Video ID from thumbnail link
                link = await renderer.query_selector("a#thumbnail")
                href = await link.get_attribute("href") if link else ""
                video_id_match = re.search(r"v=([^&]+)", href or "")
                video_id = video_id_match.group(1) if video_id_match else ""

                # Title
                title_el = await renderer.query_selector("#video-title")
                title = (await title_el.inner_text()).strip() if title_el else ""

                # Channel name
                channel_el = await renderer.query_selector(
                    "ytd-channel-name #text-container yt-formatted-string a"
                )
                if not channel_el:
                    channel_el = await renderer.query_selector("ytd-channel-name #text")
                channel = (await channel_el.inner_text()).strip() if channel_el else ""

                # Duration
                duration_el = await renderer.query_selector(
                    "ytd-thumbnail-overlay-time-status-renderer #text"
                )
                duration_text = (await duration_el.inner_text()).strip() if duration_el else ""

                # Progress bar (red bar showing watch progress)
                progress_el = await renderer.query_selector(
                    "ytd-thumbnail-overlay-resume-playback-renderer #progress"
                )
                progress_style = ""
                if progress_el:
                    progress_style = await progress_el.get_attribute("style") or ""

                # Thumbnail
                thumb_el = await renderer.query_selector("img#img")
                thumbnail_url = await thumb_el.get_attribute("src") if thumb_el else ""

                entry = parse_video_entry({
                    "video_id": video_id,
                    "title": title,
                    "channel": channel,
                    "duration_text": duration_text,
                    "progress_percent": parse_progress_bar(progress_style),
                    "thumbnail_url": thumbnail_url or "",
                })

                if entry["video_id"]:
                    videos.append(entry)

            except Exception as e:
                console.print(f"[yellow]Warning: Failed to parse a video entry: {e}[/yellow]")
                continue

        await context.close()

    return videos
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_watch_later.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: Playwright-based Watch Later scraper with progress detection"
```

---

### Task 7: Watch Later CLI Commands

**Files:**
- Create: `src/youtube_helper/watch_later/__init__.py`
- Create: `src/youtube_helper/watch_later/manager.py`
- Create: `src/youtube_helper/cli/watch_later.py`
- Test: `tests/test_watch_later_manager.py`

**Step 1: Write failing tests — tests/test_watch_later_manager.py**

```python
import sqlite3

import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.watch_later.manager import WatchLaterManager


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    """Seed the DB with a Watch Later playlist and some videos."""
    conn = get_connection(db_path)

    conn.execute(
        "INSERT INTO playlists (id, title, privacy_status, source) VALUES (?, ?, ?, ?)",
        ("WL", "Watch Later", "private", "browser"),
    )

    videos = [
        ("VID1", "Watched Fully", "Channel A", 90.0),
        ("VID2", "Watched Half", "Channel B", 50.0),
        ("VID3", "Barely Watched", "Channel C", 10.0),
        ("VID4", "Not Watched", "Channel D", 0.0),
        ("VID5", "Mostly Watched", "Channel A", 75.0),
    ]
    for vid_id, title, channel, progress in videos:
        conn.execute(
            "INSERT INTO videos (id, title, channel_name, watch_progress) VALUES (?, ?, ?, ?)",
            (vid_id, title, channel, progress),
        )
        conn.execute(
            "INSERT INTO playlist_videos (playlist_id, video_id, playlist_item_id, position) VALUES (?, ?, ?, ?)",
            ("WL", vid_id, f"PLI_{vid_id}", videos.index((vid_id, title, channel, progress))),
        )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def manager(seeded_db):
    return WatchLaterManager(seeded_db)


class TestGetWatchedVideos:
    def test_finds_videos_above_threshold(self, manager):
        watched = manager.get_watched_videos(threshold=50.0)
        ids = [v["id"] for v in watched]
        assert "VID1" in ids  # 90%
        assert "VID2" in ids  # 50%
        assert "VID5" in ids  # 75%
        assert "VID3" not in ids  # 10%
        assert "VID4" not in ids  # 0%

    def test_threshold_zero_returns_all_with_progress(self, manager):
        watched = manager.get_watched_videos(threshold=0.1)
        assert len(watched) == 4  # all except VID4


class TestGetUnwatchedVideos:
    def test_finds_videos_below_threshold(self, manager):
        unwatched = manager.get_unwatched_videos(threshold=50.0)
        ids = [v["id"] for v in unwatched]
        assert "VID3" in ids
        assert "VID4" in ids
        assert "VID1" not in ids


class TestExportPlaylistData:
    def test_exports_all_watch_later_videos(self, manager):
        data = manager.export_playlist_data("WL")
        assert len(data) == 5

    def test_export_includes_progress(self, manager):
        data = manager.export_playlist_data("WL")
        vid1 = next(v for v in data if v["id"] == "VID1")
        assert vid1["watch_progress"] == 90.0


class TestSaveScrapedVideos:
    def test_saves_scraped_data_to_db(self, db_path):
        manager = WatchLaterManager(db_path)
        scraped = [
            {
                "video_id": "NEW1",
                "title": "New Video",
                "channel": "New Channel",
                "duration_seconds": 600,
                "progress_percent": 25.0,
                "thumbnail_url": "https://example.com/thumb.jpg",
            }
        ]
        manager.save_scraped_videos(scraped)
        conn = get_connection(db_path)
        video = conn.execute("SELECT * FROM videos WHERE id = 'NEW1'").fetchone()
        assert video is not None
        assert video["title"] == "New Video"
        assert video["watch_progress"] == 25.0

        rel = conn.execute(
            "SELECT * FROM playlist_videos WHERE video_id = 'NEW1' AND playlist_id = 'WL'"
        ).fetchone()
        assert rel is not None
        conn.close()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_watch_later_manager.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/watch_later/__init__.py**

```python
```

**Step 4: Create src/youtube_helper/watch_later/manager.py**

```python
from __future__ import annotations

from youtube_helper.db.connection import get_connection


class WatchLaterManager:
    WATCH_LATER_ID = "WL"

    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_scraped_videos(self, videos: list[dict]) -> int:
        """Save scraped Watch Later videos into the database."""
        conn = get_connection(self.db_path)

        # Ensure WL playlist exists
        conn.execute(
            """INSERT INTO playlists (id, title, privacy_status, source)
               VALUES (?, 'Watch Later', 'private', 'browser')
               ON CONFLICT(id) DO UPDATE SET last_synced=datetime('now')""",
            (self.WATCH_LATER_ID,),
        )

        saved = 0
        for i, v in enumerate(videos):
            conn.execute(
                """INSERT INTO videos (id, title, channel_name, duration, watch_progress, thumbnail_url, last_synced)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(id) DO UPDATE SET
                       title=excluded.title,
                       channel_name=excluded.channel_name,
                       duration=excluded.duration,
                       watch_progress=excluded.watch_progress,
                       thumbnail_url=excluded.thumbnail_url,
                       last_synced=excluded.last_synced""",
                (
                    v["video_id"],
                    v["title"],
                    v["channel"],
                    v["duration_seconds"],
                    v["progress_percent"],
                    v.get("thumbnail_url", ""),
                ),
            )
            conn.execute(
                """INSERT INTO playlist_videos (playlist_id, video_id, playlist_item_id, position)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(playlist_id, video_id) DO UPDATE SET position=excluded.position""",
                (self.WATCH_LATER_ID, v["video_id"], "", i),
            )
            saved += 1

        conn.commit()
        conn.close()
        return saved

    def get_watched_videos(self, threshold: float = 50.0) -> list[dict]:
        """Get Watch Later videos watched at or above the threshold percentage."""
        conn = get_connection(self.db_path)
        rows = conn.execute(
            """SELECT v.* FROM videos v
               JOIN playlist_videos pv ON v.id = pv.video_id
               WHERE pv.playlist_id = ? AND v.watch_progress >= ?
               ORDER BY v.watch_progress DESC""",
            (self.WATCH_LATER_ID, threshold),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_unwatched_videos(self, threshold: float = 50.0) -> list[dict]:
        """Get Watch Later videos watched below the threshold percentage."""
        conn = get_connection(self.db_path)
        rows = conn.execute(
            """SELECT v.* FROM videos v
               JOIN playlist_videos pv ON v.id = pv.video_id
               WHERE pv.playlist_id = ? AND v.watch_progress < ?
               ORDER BY pv.position""",
            (self.WATCH_LATER_ID, threshold),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def export_playlist_data(self, playlist_id: str) -> list[dict]:
        """Export all videos from a playlist with their metadata."""
        conn = get_connection(self.db_path)
        rows = conn.execute(
            """SELECT v.*, pv.position, pv.playlist_item_id
               FROM videos v
               JOIN playlist_videos pv ON v.id = pv.video_id
               WHERE pv.playlist_id = ?
               ORDER BY pv.position""",
            (playlist_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def remove_videos_from_db(self, playlist_id: str, video_ids: list[str]) -> int:
        """Remove videos from a playlist in the local database."""
        conn = get_connection(self.db_path)
        removed = 0
        for vid in video_ids:
            conn.execute(
                "DELETE FROM playlist_videos WHERE playlist_id = ? AND video_id = ?",
                (playlist_id, vid),
            )
            removed += 1
        conn.commit()
        conn.close()
        return removed
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_watch_later_manager.py -v`
Expected: ALL PASS

**Step 6: Create src/youtube_helper/cli/watch_later.py**

```python
import asyncio
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from youtube_helper.config.settings import Settings

console = Console()


@click.group(name="wl")
def watch_later() -> None:
    """Watch Later playlist management."""
    pass


@watch_later.command()
@click.option("--headless", is_flag=True, help="Run browser in headless mode.")
def scrape(headless: bool) -> None:
    """Scrape Watch Later playlist using Playwright and save to database."""
    settings = Settings()
    settings.ensure_dirs()

    from youtube_helper.browser.watch_later import scrape_watch_later
    from youtube_helper.db.migrations import run_migrations
    from youtube_helper.watch_later.manager import WatchLaterManager

    run_migrations(str(settings.db_path))

    console.print(
        Panel(
            "[cyan]Launching Chrome to scrape Watch Later playlist.\n"
            "Your existing Chrome profile will be used for authentication.[/cyan]",
            title="[bold]Watch Later Scraper[/bold]",
            border_style="cyan",
        )
    )

    videos = asyncio.run(scrape_watch_later(headless=headless))

    manager = WatchLaterManager(str(settings.db_path))
    saved = manager.save_scraped_videos(videos)

    console.print(
        Panel(
            f"[green]Scraped and saved [bold]{saved}[/bold] videos from Watch Later[/green]",
            title="[bold]Scrape Complete[/bold]",
            border_style="green",
        )
    )


@watch_later.command()
@click.option("--threshold", "-t", default=50.0, help="Watch percentage threshold (default: 50%).")
def show_watched(threshold: float) -> None:
    """Show Watch Later videos watched above threshold."""
    settings = Settings()

    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(str(settings.db_path))
    watched = manager.get_watched_videos(threshold=threshold)

    if not watched:
        console.print(f"[yellow]No videos watched above {threshold}%[/yellow]")
        return

    table = Table(
        title=f"Watch Later — Watched ≥ {threshold}%",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold cyan", max_width=50)
    table.add_column("Channel", style="green")
    table.add_column("Progress", justify="right", style="yellow")

    for i, v in enumerate(watched, 1):
        progress = v.get("watch_progress", 0)
        bar = _progress_bar(progress)
        table.add_row(str(i), v["title"], v["channel_name"], f"{bar} {progress:.0f}%")

    console.print()
    console.print(table)
    console.print(f"\n[bold]{len(watched)}[/bold] videos watched ≥ {threshold}%")


@watch_later.command()
def show_unwatched() -> None:
    """Show Watch Later videos not yet watched."""
    settings = Settings()

    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(str(settings.db_path))
    unwatched = manager.get_unwatched_videos(threshold=50.0)

    table = Table(
        title="Watch Later — Unwatched",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold cyan", max_width=50)
    table.add_column("Channel", style="green")
    table.add_column("Progress", justify="right", style="dim")

    for i, v in enumerate(unwatched, 1):
        progress = v.get("watch_progress", 0)
        bar = _progress_bar(progress)
        table.add_row(str(i), v["title"], v["channel_name"], f"{bar} {progress:.0f}%")

    console.print()
    console.print(table)
    console.print(f"\n[bold]{len(unwatched)}[/bold] unwatched videos")


@watch_later.command()
@click.option("--threshold", "-t", default=50.0, help="Watch percentage threshold.")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes.")
@click.option("--target", default="spacepope videos", help="Target playlist name.")
def export(threshold: float, dry_run: bool, target: str) -> None:
    """Export Watch Later to a dated private playlist and optionally clean up watched videos.

    This command:
    1. Creates a dated private playlist (e.g., "Watch Later Export 2026-03-02")
    2. Copies ALL Watch Later videos into it
    3. Appends all videos to the master "Watch Later Archive" playlist
    4. Moves unwatched videos to the target playlist (default: "spacepope videos")
    5. Removes videos watched ≥ threshold from Watch Later
    """
    settings = Settings()

    from youtube_helper.api.auth import get_authenticated_service
    from youtube_helper.api.playlists import PlaylistClient
    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(str(settings.db_path))

    all_videos = manager.export_playlist_data("WL")
    watched = manager.get_watched_videos(threshold=threshold)
    unwatched = manager.get_unwatched_videos(threshold=threshold)

    if not all_videos:
        console.print("[yellow]No videos found in Watch Later. Run 'yt wl scrape' first.[/yellow]")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")

    console.print()
    console.print(
        Panel(
            f"[bold]Watch Later Export Plan[/bold]\n\n"
            f"Total videos: [bold]{len(all_videos)}[/bold]\n"
            f"Watched ≥ {threshold}%: [bold red]{len(watched)}[/bold red] (will be removed)\n"
            f"Unwatched: [bold green]{len(unwatched)}[/bold green] (will be kept/moved)\n\n"
            f"[cyan]Actions:[/cyan]\n"
            f"  1. Create [bold]'Watch Later Export {date_str}'[/bold] (all {len(all_videos)} videos)\n"
            f"  2. Append to [bold]'Watch Later Archive'[/bold] (master list)\n"
            f"  3. Copy unwatched to [bold]'{target}'[/bold]\n"
            f"  4. Remove {len(watched)} watched videos from Watch Later",
            border_style="cyan",
        )
    )

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    if not click.confirm("\nProceed with export?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    with console.status("[bold cyan]Connecting to YouTube...[/bold cyan]", spinner="dots"):
        youtube = get_authenticated_service(settings)
        client = PlaylistClient(youtube)

    # Step 1: Create dated export playlist
    console.print(f"\n[cyan]Creating 'Watch Later Export {date_str}'...[/cyan]")
    export_pl = client.create_playlist(
        f"Watch Later Export {date_str}",
        description=f"Exported from Watch Later on {date_str}",
        privacy="private",
    )
    _add_videos_to_playlist(client, export_pl["id"], all_videos, "dated export")

    # Step 2: Find or create master archive playlist
    console.print("\n[cyan]Updating 'Watch Later Archive'...[/cyan]")
    archive_id = _find_or_create_playlist(client, "Watch Later Archive")
    _add_videos_to_playlist(client, archive_id, all_videos, "master archive")

    # Step 3: Find or create target playlist, add unwatched
    console.print(f"\n[cyan]Copying unwatched to '{target}'...[/cyan]")
    target_id = _find_or_create_playlist(client, target)
    _add_videos_to_playlist(client, target_id, unwatched, target)

    # Step 4: Remove watched from Watch Later (via Playwright)
    console.print(f"\n[cyan]Removing {len(watched)} watched videos from Watch Later...[/cyan]")
    console.print(
        "[yellow]Note: Watch Later removal requires Playwright browser automation.[/yellow]"
    )
    console.print("[yellow]Run 'yt wl purge --threshold {threshold}' to remove via browser.[/yellow]")

    # Update local DB
    watched_ids = [v["id"] for v in watched]
    manager.remove_videos_from_db("WL", watched_ids)

    console.print(
        Panel(
            f"[green bold]Export complete![/green bold]\n\n"
            f"Created: [bold]Watch Later Export {date_str}[/bold] ({len(all_videos)} videos)\n"
            f"Updated: [bold]Watch Later Archive[/bold] (appended {len(all_videos)})\n"
            f"Copied: [bold]{len(unwatched)}[/bold] unwatched → [bold]{target}[/bold]\n"
            f"Removed: [bold]{len(watched)}[/bold] watched from local DB",
            title="[bold]Export Summary[/bold]",
            border_style="green",
        )
    )


@watch_later.command()
@click.option("--threshold", "-t", default=50.0, help="Watch percentage threshold.")
@click.option("--dry-run", is_flag=True, help="Show what would be removed.")
@click.option("--headless", is_flag=True, help="Run browser headless.")
def purge(threshold: float, dry_run: bool, headless: bool) -> None:
    """Remove watched videos from Watch Later via Playwright."""
    settings = Settings()

    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(str(settings.db_path))
    watched = manager.get_watched_videos(threshold=threshold)

    if not watched:
        console.print(f"[yellow]No videos watched ≥ {threshold}%. Nothing to purge.[/yellow]")
        return

    table = Table(title=f"Videos to Remove (watched ≥ {threshold}%)", border_style="red")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold", max_width=50)
    table.add_column("Channel", style="green")
    table.add_column("Progress", justify="right", style="red")

    for i, v in enumerate(watched, 1):
        table.add_row(
            str(i), v["title"], v["channel_name"], f"{v['watch_progress']:.0f}%"
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold red]{len(watched)}[/bold red] videos will be removed from Watch Later")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes made.[/yellow]")
        return

    if not click.confirm("\nProceed with removal?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    console.print("\n[cyan]Launching browser to remove videos...[/cyan]")
    asyncio.run(_purge_via_browser(watched, headless))

    # Update local DB
    manager.remove_videos_from_db("WL", [v["id"] for v in watched])

    console.print(
        Panel(
            f"[green]Removed [bold]{len(watched)}[/bold] watched videos from Watch Later[/green]",
            title="[bold]Purge Complete[/bold]",
            border_style="green",
        )
    )


@watch_later.command()
def prune_exports() -> None:
    """Remove already-watched videos from export playlists."""
    settings = Settings()

    from youtube_helper.api.auth import get_authenticated_service
    from youtube_helper.api.playlists import PlaylistClient
    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(str(settings.db_path))

    with console.status("[bold cyan]Connecting to YouTube...[/bold cyan]", spinner="dots"):
        youtube = get_authenticated_service(settings)
        client = PlaylistClient(youtube)

    # Find export playlists
    all_playlists = client.list_playlists()
    export_playlists = [
        p for p in all_playlists if p["snippet"]["title"].startswith("Watch Later Export")
    ]

    if not export_playlists:
        console.print("[yellow]No Watch Later Export playlists found.[/yellow]")
        return

    console.print(f"\n[cyan]Found {len(export_playlists)} export playlists[/cyan]\n")

    total_pruned = 0
    for pl in export_playlists:
        pl_id = pl["id"]
        pl_title = pl["snippet"]["title"]
        items = client.list_playlist_items(pl_id)

        # Check which videos have been watched (in our DB)
        prunable = []
        for item in items:
            video_id = item["snippet"]["resourceId"]["videoId"]
            conn = get_connection(str(settings.db_path))
            video = conn.execute(
                "SELECT watch_progress FROM videos WHERE id = ?", (video_id,)
            ).fetchone()
            conn.close()
            if video and video["watch_progress"] >= 50.0:
                prunable.append(item)

        if prunable:
            console.print(
                f"  [bold]{pl_title}[/bold]: {len(prunable)} watched videos to remove"
            )
            if click.confirm(f"  Remove {len(prunable)} watched videos from '{pl_title}'?"):
                for item in prunable:
                    client.remove_from_playlist(item["id"])
                total_pruned += len(prunable)
                console.print(f"  [green]✓ Removed {len(prunable)} videos[/green]")
        else:
            console.print(f"  [dim]{pl_title}: no watched videos to prune[/dim]")

    console.print(
        Panel(
            f"[green]Pruned [bold]{total_pruned}[/bold] watched videos from export playlists[/green]",
            title="[bold]Prune Complete[/bold]",
            border_style="green",
        )
    )


def _progress_bar(percent: float) -> str:
    """Render a small text progress bar."""
    filled = int(percent / 10)
    return f"[red]{'━' * filled}[/red][dim]{'━' * (10 - filled)}[/dim]"


def _find_or_create_playlist(client, title: str) -> str:
    """Find an existing playlist by title or create it."""
    playlists = client.list_playlists()
    for pl in playlists:
        if pl["snippet"]["title"] == title:
            return pl["id"]
    new_pl = client.create_playlist(title, privacy="private")
    console.print(f"  [green]Created new playlist: '{title}'[/green]")
    return new_pl["id"]


def _add_videos_to_playlist(
    client, playlist_id: str, videos: list[dict], label: str
) -> None:
    """Add videos to a playlist with progress display."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"Adding to {label}..."),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
    ) as progress:
        task = progress.add_task("Adding", total=len(videos))
        for v in videos:
            video_id = v.get("id") or v.get("video_id")
            try:
                client.add_to_playlist(playlist_id, video_id)
            except Exception as e:
                console.print(f"  [yellow]Skipped {video_id}: {e}[/yellow]")
            progress.update(task, advance=1)


async def _purge_via_browser(videos: list[dict], headless: bool) -> None:
    """Remove specific videos from Watch Later using Playwright."""
    from playwright.async_api import async_playwright

    from youtube_helper.browser.watch_later import find_chrome_profile_path

    chrome_path = find_chrome_profile_path()
    video_ids = {v["id"] for v in videos}

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto("https://www.youtube.com/playlist?list=WL", wait_until="networkidle")
        await page.wait_for_selector("ytd-playlist-video-renderer", timeout=15000)

        # Scroll to load all videos first
        for _ in range(50):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(500)

        removed = 0
        renderers = await page.query_selector_all("ytd-playlist-video-renderer")

        with Progress(
            SpinnerColumn(),
            TextColumn("Removing videos..."),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:
            task = progress.add_task("Removing", total=len(video_ids))

            for renderer in renderers:
                link = await renderer.query_selector("a#thumbnail")
                href = await link.get_attribute("href") if link else ""
                import re

                match = re.search(r"v=([^&]+)", href or "")
                if not match:
                    continue
                vid = match.group(1)

                if vid in video_ids:
                    # Click 3-dot menu
                    menu_btn = await renderer.query_selector(
                        "yt-icon-button#button, button[aria-label='Action menu']"
                    )
                    if menu_btn:
                        await menu_btn.click()
                        await page.wait_for_timeout(300)

                        # Click "Remove from Watch Later"
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
                            progress.update(task, advance=1)

        console.print(f"\n[green]Successfully removed {removed}/{len(video_ids)} videos[/green]")
        await context.close()
```

**Step 7: Register watch_later command in main.py**

Add to `src/youtube_helper/cli/main.py`:

```python
from youtube_helper.cli.watch_later import watch_later
cli.add_command(watch_later)
```

**Step 8: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: Watch Later manager with scrape, export, purge, and prune commands"
```

---

### Task 8: Fuzzy Search

**Files:**
- Create: `src/youtube_helper/search/__init__.py`
- Create: `src/youtube_helper/search/fuzzy.py`
- Create: `src/youtube_helper/cli/search.py`
- Test: `tests/test_fuzzy_search.py`

**Step 1: Write failing tests — tests/test_fuzzy_search.py**

```python
import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.search.fuzzy import FuzzySearch


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title) VALUES (?, ?)",
        ("PL1", "Programming Tutorials"),
    )
    conn.execute(
        "INSERT INTO playlists (id, title) VALUES (?, ?)",
        ("PL2", "Music Videos"),
    )
    videos = [
        ("V1", "Python Tutorial for Beginners", "Tech Channel"),
        ("V2", "Advanced Python Patterns", "Code Academy"),
        ("V3", "JavaScript Crash Course", "Web Dev"),
        ("V4", "Lo-fi Beats to Study To", "ChilledCow"),
    ]
    for vid_id, title, channel in videos:
        conn.execute(
            "INSERT INTO videos (id, title, channel_name) VALUES (?, ?, ?)",
            (vid_id, title, channel),
        )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id) VALUES ('PL1', 'V1')"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id) VALUES ('PL1', 'V2')"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id) VALUES ('PL1', 'V3')"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id) VALUES ('PL2', 'V4')"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def search(seeded_db):
    return FuzzySearch(seeded_db)


class TestSearchVideos:
    def test_finds_by_title(self, search):
        results = search.search_videos("python")
        titles = [r["title"] for r in results]
        assert "Python Tutorial for Beginners" in titles
        assert "Advanced Python Patterns" in titles

    def test_finds_by_channel(self, search):
        results = search.search_videos("tech channel")
        assert len(results) >= 1

    def test_no_results_returns_empty(self, search):
        results = search.search_videos("xyznonexistent")
        assert len(results) == 0

    def test_respects_threshold(self, search):
        results = search.search_videos("python", threshold=90)
        # Only very close matches
        assert all("Python" in r["title"] or "python" in r["title"].lower() for r in results)


class TestSearchPlaylists:
    def test_finds_by_name(self, search):
        results = search.search_playlists("programming")
        assert len(results) >= 1
        assert results[0]["title"] == "Programming Tutorials"

    def test_fuzzy_match(self, search):
        results = search.search_playlists("prog tut")
        assert len(results) >= 1


class TestSearchAll:
    def test_returns_both_types(self, search):
        results = search.search_all("music")
        types = {r["type"] for r in results}
        assert "playlist" in types or "video" in types
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fuzzy_search.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/search/__init__.py**

```python
```

**Step 4: Create src/youtube_helper/search/fuzzy.py**

```python
from __future__ import annotations

from thefuzz import fuzz, process

from youtube_helper.db.connection import get_connection


class FuzzySearch:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def search_videos(self, query: str, threshold: int = 60, limit: int = 20) -> list[dict]:
        conn = get_connection(self.db_path)
        rows = conn.execute(
            "SELECT id, title, channel_name, watch_progress, duration FROM videos"
        ).fetchall()
        conn.close()

        videos = [dict(r) for r in rows]
        if not videos:
            return []

        # Search against title and channel_name combined
        choices = {v["id"]: f"{v['title']} {v['channel_name']}" for v in videos}
        matches = process.extract(query, choices, scorer=fuzz.WRatio, limit=limit)

        results = []
        for match_text, score, vid_id in matches:
            if score >= threshold:
                video = next(v for v in videos if v["id"] == vid_id)
                video["score"] = score
                results.append(video)

        return results

    def search_playlists(self, query: str, threshold: int = 60, limit: int = 10) -> list[dict]:
        conn = get_connection(self.db_path)
        rows = conn.execute("SELECT id, title, video_count FROM playlists").fetchall()
        conn.close()

        playlists = [dict(r) for r in rows]
        if not playlists:
            return []

        choices = {p["id"]: p["title"] for p in playlists}
        matches = process.extract(query, choices, scorer=fuzz.WRatio, limit=limit)

        results = []
        for match_text, score, pl_id in matches:
            if score >= threshold:
                playlist = next(p for p in playlists if p["id"] == pl_id)
                playlist["score"] = score
                results.append(playlist)

        return results

    def search_all(self, query: str, threshold: int = 60) -> list[dict]:
        results = []

        for v in self.search_videos(query, threshold):
            v["type"] = "video"
            results.append(v)

        for p in self.search_playlists(query, threshold):
            p["type"] = "playlist"
            results.append(p)

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results
```

**Step 5: Create src/youtube_helper/cli/search.py**

```python
import click
from rich.console import Console
from rich.table import Table

from youtube_helper.config.settings import Settings

console = Console()


@click.command()
@click.argument("query")
@click.option("--videos-only", is_flag=True, help="Search only videos.")
@click.option("--playlists-only", is_flag=True, help="Search only playlists.")
@click.option("--threshold", "-t", default=60, help="Minimum match score (0-100).")
def search(query: str, videos_only: bool, playlists_only: bool, threshold: int) -> None:
    """Fuzzy search across all videos and playlists."""
    settings = Settings()

    from youtube_helper.search.fuzzy import FuzzySearch

    searcher = FuzzySearch(str(settings.db_path))

    if playlists_only:
        results = [{"type": "playlist", **p} for p in searcher.search_playlists(query, threshold)]
    elif videos_only:
        results = [{"type": "video", **v} for v in searcher.search_videos(query, threshold)]
    else:
        results = searcher.search_all(query, threshold)

    if not results:
        console.print(f"[yellow]No matches for '[bold]{query}[/bold]'[/yellow]")
        return

    table = Table(title=f"Search: '{query}'", border_style="cyan", show_lines=True)
    table.add_column("Type", style="dim", width=8)
    table.add_column("Title", style="bold cyan", max_width=50)
    table.add_column("Detail", style="green")
    table.add_column("Score", justify="right", style="yellow", width=6)

    for r in results:
        if r["type"] == "video":
            detail = r.get("channel_name", "")
        else:
            detail = f"{r.get('video_count', 0)} videos"

        type_badge = "[blue]video[/blue]" if r["type"] == "video" else "[magenta]playlist[/magenta]"
        table.add_row(type_badge, r["title"], detail, str(r.get("score", "")))

    console.print()
    console.print(table)
    console.print(f"\n[bold]{len(results)}[/bold] results")
```

**Step 6: Register search command in main.py**

Add to `src/youtube_helper/cli/main.py`:

```python
from youtube_helper.cli.search import search
cli.add_command(search)
```

**Step 7: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add -A
git commit -m "feat: fuzzy search across videos and playlists"
```

---

### Task 9: Playlist List & Show Commands (Rich Output)

**Files:**
- Create: `src/youtube_helper/cli/playlist.py`
- Test: `tests/test_playlist_cli.py`

**Step 1: Write failing tests — tests/test_playlist_cli.py**

```python
import pytest

from click.testing import CliRunner
from youtube_helper.cli.main import cli
from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title, privacy_status, video_count) VALUES (?, ?, ?, ?)",
        ("PL1", "My Favorites", "private", 10),
    )
    conn.execute(
        "INSERT INTO playlists (id, title, privacy_status, video_count) VALUES (?, ?, ?, ?)",
        ("PL2", "Watch Later Export 2026-03-02", "private", 5),
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) VALUES (?, ?, ?, ?)",
        ("V1", "Cool Video", "Cool Channel", 0.0),
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) VALUES (?, ?, ?)",
        ("PL1", "V1", 0),
    )
    conn.commit()
    conn.close()
    return db_path


class TestPlaylistList:
    def test_lists_playlists(self, seeded_db):
        runner = CliRunner()
        result = runner.invoke(cli, ["playlist", "list", "--db-path", seeded_db])
        assert result.exit_code == 0
        assert "My Favorites" in result.output

    def test_empty_db_shows_message(self, db_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["playlist", "list", "--db-path", db_path])
        assert result.exit_code == 0


class TestPlaylistShow:
    def test_shows_playlist_videos(self, seeded_db):
        runner = CliRunner()
        result = runner.invoke(cli, ["playlist", "show", "favorites", "--db-path", seeded_db])
        assert result.exit_code == 0
        assert "Cool Video" in result.output
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_playlist_cli.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/cli/playlist.py**

```python
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from youtube_helper.config.settings import Settings
from youtube_helper.db.connection import get_connection

console = Console()


@click.group()
def playlist() -> None:
    """Playlist browsing and management."""
    pass


@playlist.command(name="list")
@click.option("--db-path", default=None, help="Path to database.")
def list_playlists(db_path: str | None) -> None:
    """List all synced playlists."""
    if db_path is None:
        db_path = str(Settings().db_path)

    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM playlists ORDER BY title"
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No playlists found. Run 'yt sync' first.[/yellow]")
        return

    table = Table(title="Your Playlists", border_style="cyan", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold cyan", max_width=40)
    table.add_column("Videos", justify="right", style="green")
    table.add_column("Privacy", style="yellow")
    table.add_column("Source", style="dim")
    table.add_column("Last Synced", style="dim")

    for i, row in enumerate(rows, 1):
        privacy_style = {
            "private": "[red]private[/red]",
            "public": "[green]public[/green]",
            "unlisted": "[yellow]unlisted[/yellow]",
        }.get(row["privacy_status"], row["privacy_status"] or "")

        table.add_row(
            str(i),
            row["title"],
            str(row["video_count"] or 0),
            privacy_style,
            row["source"] or "",
            (row["last_synced"] or "never")[:10],
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold]{len(rows)}[/bold] playlists")


@playlist.command()
@click.argument("name")
@click.option("--db-path", default=None, help="Path to database.")
def show(name: str, db_path: str | None) -> None:
    """Show videos in a playlist (fuzzy matched by name)."""
    if db_path is None:
        db_path = str(Settings().db_path)

    from youtube_helper.search.fuzzy import FuzzySearch

    searcher = FuzzySearch(db_path)
    matches = searcher.search_playlists(name, threshold=50, limit=1)

    if not matches:
        console.print(f"[yellow]No playlist matching '{name}'[/yellow]")
        return

    playlist = matches[0]
    pl_id = playlist["id"]

    conn = get_connection(db_path)
    videos = conn.execute(
        """SELECT v.*, pv.position FROM videos v
           JOIN playlist_videos pv ON v.id = pv.video_id
           WHERE pv.playlist_id = ?
           ORDER BY pv.position""",
        (pl_id,),
    ).fetchall()
    conn.close()

    table = Table(
        title=f"{playlist['title']}",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold cyan", max_width=50)
    table.add_column("Channel", style="green", max_width=25)
    table.add_column("Progress", justify="right", width=16)

    for i, v in enumerate(videos, 1):
        progress = v["watch_progress"] or 0
        filled = int(progress / 10)
        bar = f"[red]{'━' * filled}[/red][dim]{'━' * (10 - filled)}[/dim] {progress:.0f}%"
        table.add_row(str(i), v["title"], v["channel_name"], bar)

    console.print()
    console.print(table)
    console.print(f"\n[bold]{len(videos)}[/bold] videos in [bold]{playlist['title']}[/bold]")
```

**Step 4: Register playlist command in main.py**

Add to `src/youtube_helper/cli/main.py`:

```python
from youtube_helper.cli.playlist import playlist
cli.add_command(playlist)
```

**Step 5: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: playlist list and show commands with Rich output"
```

---

### Task 10: Content Intelligence Stub

**Files:**
- Create: `src/youtube_helper/analyze/__init__.py`
- Create: `src/youtube_helper/analyze/stub.py`
- Create: `src/youtube_helper/cli/analyze.py`
- Test: `tests/test_analyze.py`

**Step 1: Write failing test — tests/test_analyze.py**

```python
from click.testing import CliRunner

from youtube_helper.cli.main import cli


def test_analyze_prints_coming_soon():
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "some_video"])
    assert result.exit_code == 0
    assert "coming soon" in result.output.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyze.py -v`
Expected: FAIL

**Step 3: Create src/youtube_helper/analyze/__init__.py**

```python
```

**Step 4: Create src/youtube_helper/analyze/stub.py**

```python
def analyze_video(video_id: str) -> dict:
    """Placeholder for future content intelligence.

    Future capabilities:
    - Download video audio
    - Transcribe with Whisper
    - Extract topics and key moments
    - Generate searchable transcript
    - Summarize content
    """
    return {
        "video_id": video_id,
        "status": "not_implemented",
        "message": "Content analysis coming soon",
    }
```

**Step 5: Create src/youtube_helper/cli/analyze.py**

```python
import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.argument("video")
def analyze(video: str) -> None:
    """Analyze video content (coming soon).

    Future: transcription, topic extraction, summarization.
    """
    console.print(
        Panel(
            "[yellow]Content analysis is coming soon.[/yellow]\n\n"
            "[dim]Planned features:\n"
            "  • Download and transcribe video audio (Whisper)\n"
            "  • Extract topics and key moments\n"
            "  • Generate searchable transcripts\n"
            "  • Summarize video content[/dim]",
            title="[bold]Analyze[/bold]",
            border_style="yellow",
        )
    )
```

**Step 6: Register analyze command in main.py**

Add to `src/youtube_helper/cli/main.py`:

```python
from youtube_helper.cli.analyze import analyze
cli.add_command(analyze)
```

**Step 7: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add -A
git commit -m "feat: content analysis stub (noop placeholder for future)"
```

---

### Task 11: Install Playwright & Final Integration Test

**Step 1: Install playwright browsers**

Run:
```bash
source .venv/bin/activate
playwright install chromium
```

**Step 2: Run full test suite**

Run: `pytest -v --tb=short`
Expected: ALL PASS

**Step 3: Test CLI manually**

Run:
```bash
yt --help
yt db init
yt auth status
yt wl --help
yt search --help
yt playlist --help
yt analyze test
```

**Step 4: Commit any final adjustments**

```bash
git add -A
git commit -m "chore: final integration verification"
```

---

## Summary of CLI Commands After Implementation

```
yt --help                               # Show all commands
yt --version                            # Show version
yt db init                              # Initialize database
yt db status                            # Show schema version
yt auth setup                           # Configure YouTube API auth
yt auth status                          # Show auth state
yt sync                                 # Sync all playlist metadata from YouTube API
yt wl scrape                            # Scrape Watch Later via Playwright
yt wl show-watched [--threshold 50]     # Show videos watched above threshold
yt wl show-unwatched                    # Show unwatched videos
yt wl export [--target "spacepope videos"] [--threshold 50]  # Full export workflow
yt wl purge [--threshold 50]            # Remove watched from Watch Later via browser
yt wl prune-exports                     # Remove watched from export playlists
yt search <query>                       # Fuzzy search everything
yt playlist list                        # List all playlists
yt playlist show <name>                 # Show videos in a playlist
yt analyze <video>                      # Content analysis (coming soon)
```

## Quota Budget Notes

- Sync uses `playlistItems.list` (1 unit/page) — very cheap
- Export creates playlists (50 units) and inserts videos (50 units each)
- With 5000 videos: request a quota increase from Google Cloud Console, or batch across days
- Watch Later operations use Playwright (zero API quota)
