from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable

logger = logging.getLogger("youtube_helper.browser")


def find_chrome_profile_path() -> str:
    """Find the default Chrome user data directory on macOS."""
    mac_path = (
        Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    )
    if mac_path.exists():
        return str(mac_path)
    raise FileNotFoundError("Chrome profile not found. Expected at: " + str(mac_path))


def _copy_chrome_profile(chrome_path: str) -> str:
    """Copy essential Chrome profile files to a temp dir."""
    src = Path(chrome_path)
    tmp = Path(tempfile.mkdtemp(prefix="yt-helper-chrome-"))
    local_state = src / "Local State"
    if local_state.exists():
        shutil.copy2(str(local_state), str(tmp / "Local State"))
    default_src = src / "Default"
    default_dst = tmp / "Default"
    default_dst.mkdir()
    for name in (
        "Cookies", "Cookies-journal", "Network", "Preferences",
        "Secure Preferences", "Login Data", "Login Data-journal",
        "Web Data", "Web Data-journal",
    ):
        item = default_src / name
        if item.is_dir():
            shutil.copytree(str(item), str(default_dst / name))
        elif item.exists():
            shutil.copy2(str(item), str(default_dst / name))
    return str(tmp)


async def _remove_video_from_page(page, video_id: str) -> bool:
    """Find a video by ID on the Watch Later page and click Remove."""
    renderers = await page.query_selector_all("ytd-playlist-video-renderer")
    for renderer in renderers:
        link = await renderer.query_selector("a#thumbnail")
        href = await link.get_attribute("href") if link else ""
        match = re.search(r"v=([^&]+)", href or "")
        if not match or match.group(1) != video_id:
            continue
        menu_btn = await renderer.query_selector(
            "yt-icon-button#button, button[aria-label='Action menu']"
        )
        if not menu_btn:
            return False
        await menu_btn.click()
        await page.wait_for_timeout(300)
        remove_btn = await page.query_selector(
            "tp-yt-paper-listbox ytd-menu-service-item-renderer:has-text('Remove from')"
        )
        if not remove_btn:
            remove_btn = await page.query_selector(
                "ytd-menu-service-item-renderer:has-text('Remove')"
            )
        if remove_btn:
            await remove_btn.click()
            await page.wait_for_timeout(500)
            return True
        return False
    return False


async def purge_videos_from_watch_later(
    video_ids: list[str],
    update: Callable,
    headless: bool = True,
) -> dict:
    """Remove videos from Watch Later playlist via browser automation.

    Returns dict with removed/skipped/failed counts.
    """
    from playwright.async_api import async_playwright

    chrome_path = find_chrome_profile_path()
    temp_profile = None
    removed = 0
    skipped = 0
    failed = 0

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=chrome_path, channel="chrome", headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            temp_profile = _copy_chrome_profile(chrome_path)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=temp_profile, channel="chrome", headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(
            "https://www.youtube.com/playlist?list=WL", wait_until="networkidle"
        )
        await page.wait_for_selector("ytd-playlist-video-renderer", timeout=15000)

        # Scroll to load all videos
        for _ in range(50):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(500)

        total = len(video_ids)
        for i, vid in enumerate(video_ids):
            try:
                success = await _remove_video_from_page(page, vid)
                if success:
                    removed += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.warning(f"Failed to remove {vid}: {e}")
                failed += 1
            update(
                progress=int((i + 1) / total * 100),
                message=f"Removed {removed}/{total}",
                removed=removed,
                total=total,
            )

        await context.close()

    if temp_profile:
        shutil.rmtree(temp_profile, ignore_errors=True)

    return {"removed": removed, "skipped": skipped, "failed": failed}
