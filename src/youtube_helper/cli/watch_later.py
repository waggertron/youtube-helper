import asyncio
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.table import Table

from youtube_helper.config.settings import Settings

console = Console()


def _progress_bar(percent: float) -> str:
    """Render a small text progress bar."""
    filled = int(percent / 10)
    empty = 10 - filled
    return (
        f"[red]{'━' * filled}[/red]"
        f"[dim]{'━' * empty}[/dim]"
    )


@click.group(name="wl")
def watch_later() -> None:
    """Watch Later playlist management."""


@watch_later.command(name="import")
@click.argument("file_path", type=click.Path(exists=True))
def import_takeout(file_path: str) -> None:
    """Import Watch Later from Google Takeout export file."""
    from pathlib import Path

    from youtube_helper.db.connection import get_connection
    from youtube_helper.db.migrations import run_migrations
    from youtube_helper.takeout import parse_takeout_watch_later

    settings = Settings()
    run_migrations(str(settings.db_path))

    data = Path(file_path).read_bytes()
    videos = parse_takeout_watch_later(data)

    if not videos:
        console.print("[yellow]No videos found in file.[/yellow]")
        return

    conn = get_connection(str(settings.db_path))
    conn.execute(
        "INSERT OR IGNORE INTO playlists (id, title, source) VALUES ('WL', 'Watch Later', 'takeout')"
    )
    for i, v in enumerate(videos):
        conn.execute(
            "INSERT INTO videos (id, title) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET title = excluded.title",
            (v["video_id"], v.get("title", "")),
        )
        conn.execute(
            "INSERT INTO playlist_videos (playlist_id, video_id, position) VALUES ('WL', ?, ?) "
            "ON CONFLICT(playlist_id, video_id) DO NOTHING",
            (v["video_id"], i),
        )
    conn.commit()
    conn.close()

    console.print(Panel(
        f"[green]Imported [bold]{len(videos)}[/bold] videos from Takeout file[/green]",
        title="[bold]Import Complete[/bold]",
        border_style="green",
    ))


@watch_later.command(name="show-watched")
@click.option(
    "--threshold",
    "-t",
    default=50.0,
    help="Watch percentage threshold (default: 50%).",
)
def show_watched(threshold: float) -> None:
    """Show Watch Later videos watched above threshold."""
    settings = Settings()

    from youtube_helper.watch_later.manager import (
        WatchLaterManager,
    )

    manager = WatchLaterManager(str(settings.db_path))
    watched = manager.get_watched_videos(
        threshold=threshold
    )

    if not watched:
        console.print(
            f"[yellow]No videos watched above "
            f"{threshold}%[/yellow]"
        )
        return

    table = Table(
        title=(
            f"Watch Later — Watched "
            f"\u2265 {threshold}%"
        ),
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column(
        "Title", style="bold cyan", max_width=50
    )
    table.add_column("Channel", style="green")
    table.add_column(
        "Progress", justify="right", style="yellow"
    )

    for i, v in enumerate(watched, 1):
        progress = v.get("watch_progress", 0)
        bar = _progress_bar(progress)
        table.add_row(
            str(i),
            v["title"],
            v["channel_name"],
            f"{bar} {progress:.0f}%",
        )

    console.print()
    console.print(table)
    console.print(
        f"\n[bold]{len(watched)}[/bold] videos "
        f"watched \u2265 {threshold}%"
    )


@watch_later.command(name="show-unwatched")
def show_unwatched() -> None:
    """Show Watch Later videos not yet watched."""
    settings = Settings()

    from youtube_helper.watch_later.manager import (
        WatchLaterManager,
    )

    manager = WatchLaterManager(str(settings.db_path))
    unwatched = manager.get_unwatched_videos(
        threshold=50.0
    )

    table = Table(
        title="Watch Later \u2014 Unwatched",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column(
        "Title", style="bold cyan", max_width=50
    )
    table.add_column("Channel", style="green")
    table.add_column(
        "Progress", justify="right", style="dim"
    )

    for i, v in enumerate(unwatched, 1):
        progress = v.get("watch_progress", 0)
        bar = _progress_bar(progress)
        table.add_row(
            str(i),
            v["title"],
            v["channel_name"],
            f"{bar} {progress:.0f}%",
        )

    console.print()
    console.print(table)
    console.print(
        f"\n[bold]{len(unwatched)}[/bold] "
        f"unwatched videos"
    )


@watch_later.command()
@click.option(
    "--threshold",
    "-t",
    default=50.0,
    help="Watch percentage threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without changes.",
)
@click.option(
    "--target",
    default="spacepope videos",
    help="Target playlist name.",
)
def export(
    threshold: float, dry_run: bool, target: str
) -> None:
    """Export Watch Later to dated private playlist.

    This command:
    1. Creates a dated private playlist
    2. Copies ALL Watch Later videos into it
    3. Appends to master "Watch Later Archive"
    4. Copies unwatched to target playlist
    5. Removes watched videos from Watch Later DB
    """
    settings = Settings()

    from youtube_helper.api.auth import (
        get_authenticated_service,
    )
    from youtube_helper.api.playlists import (
        PlaylistClient,
    )
    from youtube_helper.watch_later.manager import (
        WatchLaterManager,
    )

    manager = WatchLaterManager(str(settings.db_path))
    all_videos = manager.export_playlist_data("WL")
    watched = manager.get_watched_videos(
        threshold=threshold
    )
    unwatched = manager.get_unwatched_videos(
        threshold=threshold
    )

    if not all_videos:
        console.print(
            "[yellow]No videos found in Watch Later. "
            "Run 'yt wl scrape' first.[/yellow]"
        )
        return

    date_str = datetime.now().strftime("%Y-%m-%d")

    console.print()
    console.print(
        Panel(
            f"[bold]Watch Later Export Plan[/bold]\n\n"
            f"Total videos: "
            f"[bold]{len(all_videos)}[/bold]\n"
            f"Watched \u2265 {threshold}%: "
            f"[bold red]{len(watched)}[/bold red] "
            f"(will be removed)\n"
            f"Unwatched: "
            f"[bold green]{len(unwatched)}[/bold green]"
            f" (will be kept/moved)\n\n"
            f"[cyan]Actions:[/cyan]\n"
            f"  1. Create [bold]'Watch Later Export "
            f"{date_str}'[/bold] "
            f"(all {len(all_videos)} videos)\n"
            f"  2. Append to "
            f"[bold]'Watch Later Archive'[/bold]\n"
            f"  3. Copy unwatched to "
            f"[bold]'{target}'[/bold]\n"
            f"  4. Remove {len(watched)} watched "
            f"from Watch Later",
            border_style="cyan",
        )
    )

    if dry_run:
        console.print(
            "\n[yellow]Dry run "
            "\u2014 no changes made.[/yellow]"
        )
        return

    if not click.confirm("\nProceed with export?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    with console.status(
        "[bold cyan]Connecting to YouTube..."
        "[/bold cyan]",
        spinner="dots",
    ):
        youtube = get_authenticated_service(settings)
        client = PlaylistClient(youtube)

    # Step 1: Create dated export playlist
    console.print(
        f"\n[cyan]Creating 'Watch Later Export "
        f"{date_str}'...[/cyan]"
    )
    export_pl = client.create_playlist(
        f"Watch Later Export {date_str}",
        description=(
            f"Exported from Watch Later on {date_str}"
        ),
        privacy="private",
    )
    _add_videos_to_playlist(
        client,
        export_pl["id"],
        all_videos,
        "dated export",
    )

    # Step 2: Find or create master archive
    console.print(
        "\n[cyan]Updating "
        "'Watch Later Archive'...[/cyan]"
    )
    archive_id = _find_or_create_playlist(
        client, "Watch Later Archive"
    )
    _add_videos_to_playlist(
        client,
        archive_id,
        all_videos,
        "master archive",
    )

    # Step 3: Copy unwatched to target
    console.print(
        f"\n[cyan]Copying unwatched to "
        f"'{target}'...[/cyan]"
    )
    target_id = _find_or_create_playlist(client, target)
    _add_videos_to_playlist(
        client, target_id, unwatched, target
    )

    # Step 4: Remove watched from local DB
    watched_ids = [v["id"] for v in watched]
    manager.remove_videos_from_db("WL", watched_ids)

    console.print(
        Panel(
            f"[green bold]Export complete!"
            f"[/green bold]\n\n"
            f"Created: [bold]Watch Later Export "
            f"{date_str}[/bold] "
            f"({len(all_videos)} videos)\n"
            f"Updated: [bold]Watch Later "
            f"Archive[/bold] "
            f"(appended {len(all_videos)})\n"
            f"Copied: [bold]{len(unwatched)}[/bold] "
            f"unwatched \u2192 [bold]{target}[/bold]\n"
            f"Removed: [bold]{len(watched)}[/bold] "
            f"watched from local DB",
            title="[bold]Export Summary[/bold]",
            border_style="green",
        )
    )


@watch_later.command()
@click.option(
    "--threshold",
    "-t",
    default=50.0,
    help="Watch percentage threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed.",
)
@click.option(
    "--headless",
    is_flag=True,
    help="Run browser headless.",
)
def purge(
    threshold: float, dry_run: bool, headless: bool
) -> None:
    """Remove watched videos from Watch Later."""
    settings = Settings()

    from youtube_helper.watch_later.manager import (
        WatchLaterManager,
    )

    manager = WatchLaterManager(str(settings.db_path))
    watched = manager.get_watched_videos(
        threshold=threshold
    )

    if not watched:
        console.print(
            f"[yellow]No videos watched "
            f"\u2265 {threshold}%. "
            f"Nothing to purge.[/yellow]"
        )
        return

    table = Table(
        title=(
            f"Videos to Remove "
            f"(watched \u2265 {threshold}%)"
        ),
        border_style="red",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column(
        "Title", style="bold", max_width=50
    )
    table.add_column("Channel", style="green")
    table.add_column(
        "Progress", justify="right", style="red"
    )

    for i, v in enumerate(watched, 1):
        table.add_row(
            str(i),
            v["title"],
            v["channel_name"],
            f"{v['watch_progress']:.0f}%",
        )

    console.print()
    console.print(table)
    console.print(
        f"\n[bold red]{len(watched)}[/bold red] videos "
        f"will be removed from Watch Later"
    )

    if dry_run:
        console.print(
            "\n[yellow]Dry run "
            "\u2014 no changes made.[/yellow]"
        )
        return

    if not click.confirm("\nProceed with removal?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    console.print(
        "\n[cyan]Launching browser to remove "
        "videos...[/cyan]"
    )

    from youtube_helper.browser.watch_later import (
        purge_videos_from_watch_later,
    )

    def progress_update(**kwargs):
        # Simple progress callback for CLI
        pass

    result = asyncio.run(purge_videos_from_watch_later(
        video_ids=[v["id"] for v in watched],
        update=progress_update,
        headless=headless,
    ))

    manager.remove_videos_from_db(
        "WL", [v["id"] for v in watched]
    )

    console.print(
        Panel(
            f"[green]Removed "
            f"[bold]{result['removed']}[/bold] "
            f"watched videos from "
            f"Watch Later[/green]",
            title="[bold]Purge Complete[/bold]",
            border_style="green",
        )
    )


def _find_or_create_playlist(
    client, title: str
) -> str:
    """Find existing playlist by title or create."""
    playlists = client.list_playlists()
    for pl in playlists:
        if pl["snippet"]["title"] == title:
            return pl["id"]
    new_pl = client.create_playlist(
        title, privacy="private"
    )
    console.print(
        f"  [green]Created new playlist: "
        f"'{title}'[/green]"
    )
    return new_pl["id"]


def _add_videos_to_playlist(
    client,
    playlist_id: str,
    videos: list[dict],
    label: str,
) -> None:
    """Add videos to a playlist with progress."""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"Adding to {label}..."),
        BarColumn(),
        TextColumn(
            "{task.completed}/{task.total}"
        ),
    ) as progress:
        task = progress.add_task(
            "Adding", total=len(videos)
        )
        for v in videos:
            vid = v.get("id") or v.get("video_id")
            try:
                client.add_to_playlist(
                    playlist_id, vid
                )
            except Exception as e:
                console.print(
                    f"  [yellow]Skipped "
                    f"{vid}: {e}[/yellow]"
                )
            progress.update(task, advance=1)


