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
