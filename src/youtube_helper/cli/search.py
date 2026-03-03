import click
from rich.console import Console
from rich.table import Table

from youtube_helper.config.settings import Settings

console = Console()


@click.command()
@click.argument("query")
@click.option(
    "--videos-only",
    is_flag=True,
    help="Search only videos.",
)
@click.option(
    "--playlists-only",
    is_flag=True,
    help="Search only playlists.",
)
@click.option(
    "--threshold",
    "-t",
    default=60,
    help="Minimum match score (0-100).",
)
def search(
    query: str,
    videos_only: bool,
    playlists_only: bool,
    threshold: int,
) -> None:
    """Fuzzy search across all videos and playlists."""
    settings = Settings()

    from youtube_helper.search.fuzzy import FuzzySearch

    searcher = FuzzySearch(str(settings.db_path))

    if playlists_only:
        results = [
            {"type": "playlist", **p}
            for p in searcher.search_playlists(query, threshold)
        ]
    elif videos_only:
        results = [
            {"type": "video", **v}
            for v in searcher.search_videos(query, threshold)
        ]
    else:
        results = searcher.search_all(query, threshold)

    if not results:
        console.print(
            f"[yellow]No matches for '[bold]{query}[/bold]'[/yellow]"
        )
        return

    table = Table(
        title=f"Search: '{query}'",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Type", style="dim", width=8)
    table.add_column("Title", style="bold cyan", max_width=50)
    table.add_column("Detail", style="green")
    table.add_column(
        "Score",
        justify="right",
        style="yellow",
        width=6,
    )

    for r in results:
        if r["type"] == "video":
            detail = r.get("channel_name", "")
        else:
            detail = f"{r.get('video_count', 0)} videos"

        type_badge = (
            "[blue]video[/blue]"
            if r["type"] == "video"
            else "[magenta]list[/magenta]"
        )
        table.add_row(
            type_badge,
            r["title"],
            detail,
            str(r.get("score", "")),
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold]{len(results)}[/bold] results")
