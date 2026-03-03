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
        console.print(Panel(
            f"[green]Database initialized at [bold]{db_path}[/bold]\n"
            f"Applied {len(applied)} migration(s): {applied}[/green]",
            title="[bold]Database Ready[/bold]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[cyan]Database at [bold]{db_path}[/bold] is already up to date.[/cyan]",
            title="[bold]Database Status[/bold]",
            border_style="cyan",
        ))


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
    console.print(Panel(
        f"[cyan]Schema version:[/cyan] [bold]{version}[/bold]",
        title="[bold]Database Status[/bold]",
        border_style="cyan",
    ))
