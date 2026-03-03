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


@watch_later.command()
@click.option(
    "--headless",
    is_flag=True,
    help="Run browser in headless mode.",
)
def scrape(headless: bool) -> None:
    """Scrape Watch Later playlist via Playwright."""
    settings = Settings()
    settings.ensure_dirs()

    from youtube_helper.browser.watch_later import (
        scrape_watch_later,
    )
    from youtube_helper.db.migrations import run_migrations
    from youtube_helper.watch_later.manager import (
        WatchLaterManager,
    )

    run_migrations(str(settings.db_path))

    console.print(
        Panel(
            "[cyan]Launching Chrome to scrape "
            "Watch Later playlist.\n"
            "Your existing Chrome profile will be "
            "used for authentication.[/cyan]",
            title="[bold]Watch Later Scraper[/bold]",
            border_style="cyan",
        )
    )

    videos = asyncio.run(
        scrape_watch_later(headless=headless)
    )

    manager = WatchLaterManager(str(settings.db_path))
    saved = manager.save_scraped_videos(videos)

    console.print(
        Panel(
            f"[green]Scraped and saved "
            f"[bold]{saved}[/bold] videos "
            f"from Watch Later[/green]",
            title="[bold]Scrape Complete[/bold]",
            border_style="green",
        )
    )


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
    asyncio.run(_purge_via_browser(watched, headless))

    manager.remove_videos_from_db(
        "WL", [v["id"] for v in watched]
    )

    console.print(
        Panel(
            f"[green]Removed "
            f"[bold]{len(watched)}[/bold] "
            f"watched videos from "
            f"Watch Later[/green]",
            title="[bold]Purge Complete[/bold]",
            border_style="green",
        )
    )


@watch_later.command(name="prune-exports")
def prune_exports() -> None:
    """Remove watched videos from export playlists."""
    settings = Settings()

    from youtube_helper.api.auth import (
        get_authenticated_service,
    )
    from youtube_helper.api.playlists import (
        PlaylistClient,
    )
    from youtube_helper.db.connection import (
        get_connection,
    )

    with console.status(
        "[bold cyan]Connecting to YouTube..."
        "[/bold cyan]",
        spinner="dots",
    ):
        youtube = get_authenticated_service(settings)
        client = PlaylistClient(youtube)

    all_playlists = client.list_playlists()
    export_playlists = [
        p
        for p in all_playlists
        if p["snippet"]["title"].startswith(
            "Watch Later Export"
        )
    ]

    if not export_playlists:
        console.print(
            "[yellow]No Watch Later Export "
            "playlists found.[/yellow]"
        )
        return

    console.print(
        f"\n[cyan]Found {len(export_playlists)} "
        f"export playlists[/cyan]\n"
    )

    total_pruned = 0
    for pl in export_playlists:
        pl_id = pl["id"]
        pl_title = pl["snippet"]["title"]
        items = client.list_playlist_items(pl_id)

        prunable = []
        for item in items:
            vid_id = item["snippet"]["resourceId"][
                "videoId"
            ]
            conn = get_connection(
                str(settings.db_path)
            )
            video = conn.execute(
                "SELECT watch_progress FROM videos "
                "WHERE id = ?",
                (vid_id,),
            ).fetchone()
            conn.close()
            if video and video["watch_progress"] >= 50.0:
                prunable.append(item)

        if prunable:
            console.print(
                f"  [bold]{pl_title}[/bold]: "
                f"{len(prunable)} watched videos "
                f"to remove"
            )
            if click.confirm(
                f"  Remove {len(prunable)} watched "
                f"videos from '{pl_title}'?"
            ):
                for item in prunable:
                    client.remove_from_playlist(
                        item["id"]
                    )
                total_pruned += len(prunable)
                console.print(
                    f"  [green]Removed "
                    f"{len(prunable)} videos[/green]"
                )
        else:
            console.print(
                f"  [dim]{pl_title}: no watched "
                f"videos to prune[/dim]"
            )

    console.print(
        Panel(
            f"[green]Pruned "
            f"[bold]{total_pruned}[/bold] "
            f"watched videos from "
            f"export playlists[/green]",
            title="[bold]Prune Complete[/bold]",
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


async def _purge_via_browser(
    videos: list[dict], headless: bool
) -> None:
    """Remove videos from Watch Later via browser."""
    import re

    from playwright.async_api import async_playwright

    from youtube_helper.browser.watch_later import (
        find_chrome_profile_path,
    )

    chrome_path = find_chrome_profile_path()
    video_ids = {v["id"] for v in videos}

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            channel="chrome",
            headless=headless,
            args=[
                "--disable-blink-features="
                "AutomationControlled"
            ],
        )
        page = (
            ctx.pages[0]
            if ctx.pages
            else await ctx.new_page()
        )

        await page.goto(
            "https://www.youtube.com/playlist?list=WL",
            wait_until="networkidle",
        )
        await page.wait_for_selector(
            "ytd-playlist-video-renderer",
            timeout=15000,
        )

        for _ in range(50):
            await page.evaluate(
                "window.scrollBy(0, window.innerHeight)"
            )
            await page.wait_for_timeout(500)

        removed = 0
        renderers = await page.query_selector_all(
            "ytd-playlist-video-renderer"
        )

        for renderer in renderers:
            link = await renderer.query_selector(
                "a#thumbnail"
            )
            href = (
                await link.get_attribute("href")
                if link
                else ""
            )
            match = re.search(r"v=([^&]+)", href or "")
            if not match:
                continue
            vid = match.group(1)

            if vid in video_ids:
                menu_btn = await renderer.query_selector(
                    "yt-icon-button#button, "
                    "button[aria-label='Action menu']"
                )
                if menu_btn:
                    await menu_btn.click()
                    await page.wait_for_timeout(300)

                    sel = (
                        "tp-yt-paper-listbox "
                        "ytd-menu-service-item-renderer"
                        ":has-text('Remove from')"
                    )
                    remove_btn = (
                        await page.query_selector(sel)
                    )
                    if not remove_btn:
                        sel2 = (
                            "ytd-menu-service-item-"
                            "renderer"
                            ":has-text('Remove')"
                        )
                        remove_btn = (
                            await page.query_selector(
                                sel2
                            )
                        )
                    if remove_btn:
                        await remove_btn.click()
                        await page.wait_for_timeout(500)
                        removed += 1

        console.print(
            f"\n[green]Removed {removed}/"
            f"{len(video_ids)} videos[/green]"
        )
        await ctx.close()
