import click
from rich.console import Console
from rich.table import Table

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
        console.print(
            "[yellow]No playlists found. "
            "Run 'yt sync' first.[/yellow]"
        )
        return

    table = Table(
        title="Your Playlists",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column(
        "Title", style="bold cyan", max_width=40
    )
    table.add_column(
        "Videos", justify="right", style="green"
    )
    table.add_column("Privacy", style="yellow")
    table.add_column("Source", style="dim")
    table.add_column("Last Synced", style="dim")

    for i, row in enumerate(rows, 1):
        privacy_style = {
            "private": "[red]private[/red]",
            "public": "[green]public[/green]",
            "unlisted": "[yellow]unlisted[/yellow]",
        }.get(
            row["privacy_status"],
            row["privacy_status"] or "",
        )
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
@click.option(
    "--db-path", default=None, help="Path to database."
)
def show(name: str, db_path: str | None) -> None:
    """Show videos in a playlist (fuzzy matched by name)."""
    if db_path is None:
        db_path = str(Settings().db_path)

    from youtube_helper.search.fuzzy import FuzzySearch

    searcher = FuzzySearch(db_path)
    matches = searcher.search_playlists(
        name, threshold=50, limit=1
    )

    if not matches:
        console.print(
            f"[yellow]No playlist matching "
            f"'{name}'[/yellow]"
        )
        return

    pl = matches[0]
    pl_id = pl["id"]

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
        title=pl["title"],
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column(
        "Title", style="bold cyan", max_width=50
    )
    table.add_column(
        "Channel", style="green", max_width=25
    )
    table.add_column(
        "Progress", justify="right", width=16
    )

    for i, v in enumerate(videos, 1):
        progress = v["watch_progress"] or 0
        filled = int(progress / 10)
        bar = (
            f"[red]{'━' * filled}[/red]"
            f"[dim]{'━' * (10 - filled)}[/dim]"
            f" {progress:.0f}%"
        )
        table.add_row(
            str(i), v["title"], v["channel_name"], bar
        )

    console.print()
    console.print(table)
    console.print(
        f"\n[bold]{len(videos)}[/bold] videos in "
        f"[bold]{pl['title']}[/bold]"
    )
