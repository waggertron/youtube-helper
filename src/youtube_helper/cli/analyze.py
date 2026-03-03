import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.argument("video")
def analyze(video: str) -> None:
    """Analyze video content (coming soon)."""
    console.print(
        Panel(
            "[yellow]Content analysis is coming soon."
            "[/yellow]\n\n"
            "[dim]Planned features:\n"
            "  - Download and transcribe (Whisper)\n"
            "  - Extract topics and key moments\n"
            "  - Generate searchable transcripts\n"
            "  - Summarize video content[/dim]",
            title="[bold]Analyze[/bold]",
            border_style="yellow",
        )
    )
