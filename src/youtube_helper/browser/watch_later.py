from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path


def parse_duration_text(text: str) -> int:
    """Convert duration string like '10:30' or '1:30:00' to seconds."""
    if not text or not text.strip():
        return 0
    parts = text.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
    except ValueError:
        return 0
    return 0


def parse_progress_bar(style_attr: str) -> float:
    """Extract percentage from a style attribute like 'width: 75%'."""
    if not style_attr:
        return 0.0
    match = re.search(r"width:\s*([\d.]+)%", style_attr)
    if match:
        return float(match.group(1))
    return 0.0


def parse_video_entry(entry: dict) -> dict:
    """Normalize a scraped video entry."""
    return {
        "video_id": entry["video_id"],
        "title": entry["title"],
        "channel": entry["channel"],
        "duration_seconds": parse_duration_text(
            entry.get("duration_text", "")
        ),
        "progress_percent": entry.get("progress_percent", 0.0),
        "thumbnail_url": entry.get("thumbnail_url", ""),
    }


def find_chrome_profile_path() -> str:
    """Find the default Chrome user data directory on macOS."""
    mac_path = (
        Path.home()
        / "Library"
        / "Application Support"
        / "Google"
        / "Chrome"
    )
    if mac_path.exists():
        return str(mac_path)
    raise FileNotFoundError(
        "Chrome profile not found. Expected at: " + str(mac_path)
    )


def _copy_chrome_profile(chrome_path: str) -> str:
    """Copy essential Chrome profile files to a temp dir.

    This allows Playwright to use the profile while Chrome is running,
    avoiding the ProcessSingleton lock conflict.
    """
    src = Path(chrome_path)
    tmp = Path(tempfile.mkdtemp(prefix="yt-helper-chrome-"))

    # Copy Local State (top-level, needed for cookie decryption)
    local_state = src / "Local State"
    if local_state.exists():
        shutil.copy2(str(local_state), str(tmp / "Local State"))

    # Copy the Default profile's essential files
    default_src = src / "Default"
    default_dst = tmp / "Default"
    default_dst.mkdir()

    for name in (
        "Cookies",
        "Cookies-journal",
        "Network",
        "Preferences",
        "Secure Preferences",
        "Login Data",
        "Login Data-journal",
        "Web Data",
        "Web Data-journal",
    ):
        item = default_src / name
        if item.is_dir():
            shutil.copytree(str(item), str(default_dst / name))
        elif item.exists():
            shutil.copy2(str(item), str(default_dst / name))

    return str(tmp)


async def scrape_watch_later(
    max_videos: int = 5000,
    headless: bool = False,
) -> list[dict]:
    """Scrape the Watch Later playlist using Playwright with Chrome profile.

    This function launches Chrome with the user's existing profile
    (so they're already logged into YouTube) and scrapes the Watch Later
    playlist page, extracting video metadata and watch progress.
    """
    from playwright.async_api import async_playwright
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
    )

    console = Console()
    chrome_path = find_chrome_profile_path()
    videos: list[dict] = []
    temp_profile: str | None = None

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=chrome_path,
                channel="chrome",
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            # Chrome is likely running — copy profile to temp dir
            console.print(
                "[yellow]Chrome is running, using profile copy...[/yellow]"
            )
            temp_profile = _copy_chrome_profile(chrome_path)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=temp_profile,
                channel="chrome",
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        page = (
            context.pages[0]
            if context.pages
            else await context.new_page()
        )

        console.print("[cyan]Navigating to Watch Later...[/cyan]")
        await page.goto(
            "https://www.youtube.com/playlist?list=WL",
            wait_until="networkidle",
        )

        await page.wait_for_selector(
            "ytd-playlist-video-renderer", timeout=15000
        )

        # Scroll to load all videos
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 100

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} videos"),
        ) as progress:
            task = progress.add_task(
                "Scrolling to load videos...", total=max_videos
            )

            while scroll_attempts < max_scroll_attempts:
                renderers = await page.query_selector_all(
                    "ytd-playlist-video-renderer"
                )
                current_count = len(renderers)
                progress.update(task, completed=current_count)

                if current_count >= max_videos:
                    break
                if current_count == last_count:
                    scroll_attempts += 1
                    if scroll_attempts > 5:
                        break
                else:
                    scroll_attempts = 0

                last_count = current_count
                await page.evaluate(
                    "window.scrollBy(0, window.innerHeight)"
                )
                await page.wait_for_timeout(800)

        renderers = await page.query_selector_all(
            "ytd-playlist-video-renderer"
        )

        console.print(
            f"[cyan]Extracting data from "
            f"{len(renderers)} videos...[/cyan]"
        )

        for renderer in renderers:
            try:
                link = await renderer.query_selector("a#thumbnail")
                href = (
                    await link.get_attribute("href") if link else ""
                )
                video_id_match = re.search(r"v=([^&]+)", href or "")
                video_id = (
                    video_id_match.group(1) if video_id_match else ""
                )

                title_el = await renderer.query_selector(
                    "#video-title"
                )
                title = (
                    (await title_el.inner_text()).strip()
                    if title_el
                    else ""
                )

                channel_el = await renderer.query_selector(
                    "ytd-channel-name #text-container "
                    "yt-formatted-string a"
                )
                if not channel_el:
                    channel_el = await renderer.query_selector(
                        "ytd-channel-name #text"
                    )
                channel = (
                    (await channel_el.inner_text()).strip()
                    if channel_el
                    else ""
                )

                # Try multiple selectors for duration
                # (YouTube's DOM changes frequently)
                duration_el = await renderer.query_selector(
                    "ytd-thumbnail-overlay-time-status-renderer #text"
                )
                if not duration_el:
                    duration_el = await renderer.query_selector(
                        "ytd-thumbnail-overlay-time-status-renderer"
                        " span"
                    )
                if not duration_el:
                    duration_el = await renderer.query_selector(
                        "#overlays"
                        " ytd-thumbnail-overlay-time-status-renderer"
                    )
                duration_text = (
                    (await duration_el.inner_text()).strip()
                    if duration_el
                    else ""
                )

                progress_el = await renderer.query_selector(
                    "ytd-thumbnail-overlay-resume-playback-renderer"
                    " #progress"
                )
                progress_style = ""
                if progress_el:
                    progress_style = (
                        await progress_el.get_attribute("style")
                        or ""
                    )

                thumb_el = await renderer.query_selector(
                    "img#img"
                )
                thumbnail_url = (
                    await thumb_el.get_attribute("src")
                    if thumb_el
                    else ""
                )

                entry = parse_video_entry(
                    {
                        "video_id": video_id,
                        "title": title,
                        "channel": channel,
                        "duration_text": duration_text,
                        "progress_percent": parse_progress_bar(
                            progress_style
                        ),
                        "thumbnail_url": thumbnail_url or "",
                    }
                )

                if entry["video_id"]:
                    videos.append(entry)

            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to parse "
                    f"a video entry: {e}[/yellow]"
                )
                continue

        await context.close()

    if temp_profile:
        shutil.rmtree(temp_profile, ignore_errors=True)

    return videos
