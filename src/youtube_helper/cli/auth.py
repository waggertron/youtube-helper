import shutil

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from youtube_helper.config.settings import Settings

console = Console()


@click.group()
def auth() -> None:
    """Authentication and API setup."""


@auth.command()
def setup() -> None:
    """Set up YouTube API authentication."""
    settings = Settings()
    console.print()
    console.print(Panel(
        "[bold cyan]YouTube API Setup Guide[/bold cyan]\n\n"
        "Follow these steps to configure API access:\n\n"
        "[bold]1.[/bold] Go to [link=https://console.cloud.google.com]console.cloud.google.com[/link]\n"
        "[bold]2.[/bold] Create a new project (or select existing)\n"
        "[bold]3.[/bold] Enable [bold]YouTube Data API v3[/bold]\n"
        "   -> APIs & Services -> Library -> search 'YouTube Data API v3'\n"
        "[bold]4.[/bold] Create OAuth credentials\n"
        "   -> APIs & Services -> Credentials -> Create Credentials -> OAuth Client ID\n"
        "   -> Application type: [bold]Desktop app[/bold]\n"
        "[bold]5.[/bold] Download the JSON file\n"
        "[bold]6.[/bold] Configure OAuth consent screen\n"
        "   -> Add yourself as a test user\n"
        "   -> Add scope: youtube.com/auth/youtube",
        title="[bold]Setup Instructions[/bold]",
        border_style="cyan",
    ))
    client_secret = click.prompt(
        "\nPath to your client_secret JSON file",
        type=click.Path(exists=True),
    )
    settings.ensure_dirs()
    shutil.copy2(client_secret, settings.client_secret_path)
    console.print(f"\n[green]Client secret saved to {settings.client_secret_path}[/green]")
    console.print("\n[cyan]Starting OAuth flow -- a browser window will open...[/cyan]\n")

    from youtube_helper.api.auth import get_authenticated_service

    try:
        youtube = get_authenticated_service(settings)
        channel = youtube.channels().list(part="snippet", mine=True).execute()
        if channel["items"]:
            name = channel["items"][0]["snippet"]["title"]
            console.print(Panel(
                f"[green]Authenticated as [bold]{name}[/bold][/green]",
                title="[bold]Success[/bold]",
                border_style="green",
            ))
        else:
            console.print("[green]Authentication successful[/green]")
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
    table.add_row("Config Dir", str(settings.config_dir))

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
