import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--port", default=8000, help="Port to run the server on.")
@click.option("--no-browser", is_flag=True, help="Don't open the browser automatically.")
@click.option("--dev", is_flag=True, help="Run in development mode (no static serving).")
def web(port: int, no_browser: bool, dev: bool) -> None:
    """Start the web dashboard server."""
    import uvicorn

    from youtube_helper.config.settings import Settings
    from youtube_helper.db.migrations import run_migrations

    settings = Settings()
    settings.ensure_dirs()
    run_migrations(str(settings.db_path))

    console.print(Panel(
        f"[cyan]Starting YouTube Helper dashboard on "
        f"[bold]http://localhost:{port}[/bold][/cyan]",
        title="[bold]Web Dashboard[/bold]",
        border_style="cyan",
    ))

    if not no_browser and not dev:
        import threading
        import time
        import webbrowser

        def open_browser():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "youtube_helper.web.app:create_app",
        host="127.0.0.1",
        port=port,
        reload=dev,
        factory=True,
    )
