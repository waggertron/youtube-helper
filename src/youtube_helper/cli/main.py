import click
from rich.console import Console

from youtube_helper.cli.analyze import analyze
from youtube_helper.cli.auth import auth
from youtube_helper.cli.db import db
from youtube_helper.cli.playlist import playlist
from youtube_helper.cli.search import search
from youtube_helper.cli.sync import sync
from youtube_helper.cli.watch_later import watch_later
from youtube_helper.cli.web import web

console = Console()


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """yt — YouTube Helper CLI for managing playlists and content."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


cli.add_command(analyze)
cli.add_command(auth)
cli.add_command(db)
cli.add_command(playlist)
cli.add_command(search)
cli.add_command(sync)
cli.add_command(watch_later)
cli.add_command(web)
