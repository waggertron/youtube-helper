import click
from rich.console import Console
from rich.panel import Panel

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

    with console.status(
        "[bold cyan]Connecting to YouTube...[/bold cyan]",
        spinner="dots",
    ):
        youtube = get_authenticated_service(settings)
        client = PlaylistClient(youtube)

    engine = SyncEngine(str(settings.db_path), client)

    console.print(
        "\n[bold cyan]Syncing playlists and videos...[/bold cyan]\n"
    )
    stats = engine.sync_all(
        verbose=ctx.obj.get("verbose", False)
    )

    console.print(
        Panel(
            f"[green]Synced [bold]{stats['playlists']}[/bold] "
            f"playlists, "
            f"[bold]{stats['videos']}[/bold] videos[/green]",
            title="[bold]Sync Complete[/bold]",
            border_style="green",
        )
    )
