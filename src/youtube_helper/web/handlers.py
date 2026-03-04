"""Operation handlers for the queue processor.

Each handler is an async function with signature:
    async def handler(params: dict, progress: Callable) -> None
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from youtube_helper.web.processor import QueueProcessor


def register_all_handlers(processor: QueueProcessor) -> None:
    """Register all operation handlers with the queue processor."""
    processor.register_handler("sync", handle_sync)
    processor.register_handler("scrape_watch_later", handle_scrape)
    processor.register_handler("export_watch_later", handle_export)
    processor.register_handler("purge_watch_later", handle_purge)
    processor.register_handler("prune_exports", handle_prune_exports)
    processor.register_handler("create_playlist", handle_create_playlist)
    processor.register_handler("delete_playlist", handle_delete_playlist)
    processor.register_handler("add_videos", handle_add_videos)
    processor.register_handler("remove_video", handle_remove_video)
    processor.register_handler("reorder_playlist", handle_reorder)
    processor.register_handler("like_video", handle_like)
    processor.register_handler("unlike_video", handle_unlike)


def _get_youtube_client(db_path: str):
    """Create an authenticated YouTube client and PlaylistClient."""
    from youtube_helper.api.auth import get_authenticated_service
    from youtube_helper.api.playlists import PlaylistClient
    from youtube_helper.config.settings import Settings

    settings = Settings()
    youtube = get_authenticated_service(settings)
    return youtube, PlaylistClient(youtube)


async def handle_sync(params, progress):
    """Sync all playlists from YouTube."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.sync.engine import SyncEngine

    settings = Settings()
    db_path = str(settings.db_path)
    await progress(10.0, "Connecting to YouTube...")
    _, client = _get_youtube_client(db_path)
    await progress(20.0, "Syncing playlists...")
    engine = SyncEngine(db_path, client)
    stats = engine.sync_all()
    await progress(
        100.0,
        f"Synced {stats['playlists']} playlists, {stats['videos']} videos",
    )


async def handle_scrape(params, progress):
    """Scrape Watch Later playlist via browser automation."""
    from youtube_helper.browser.watch_later import scrape_watch_later
    from youtube_helper.config.settings import Settings
    from youtube_helper.watch_later.manager import WatchLaterManager

    settings = Settings()
    await progress(10.0, "Launching Chrome...")
    videos = await scrape_watch_later(
        headless=params.get("headless", False),
    )
    await progress(80.0, f"Scraped {len(videos)} videos, saving...")
    manager = WatchLaterManager(str(settings.db_path))
    saved = manager.save_scraped_videos(videos)
    await progress(100.0, f"Saved {saved} videos")


async def handle_export(params, progress):
    """Export Watch Later playlist to YouTube playlists."""
    from datetime import datetime

    from youtube_helper.config.settings import Settings
    from youtube_helper.watch_later.manager import WatchLaterManager

    settings = Settings()
    db_path = str(settings.db_path)
    threshold = params.get("threshold", 50.0)
    target = params.get("target", "spacepope videos")
    manager = WatchLaterManager(db_path)
    all_videos = manager.export_playlist_data("WL")
    watched = manager.get_watched_videos(threshold=threshold)
    unwatched = manager.get_unwatched_videos(threshold=threshold)

    if not all_videos:
        await progress(100.0, "No videos found in Watch Later")
        return

    await progress(10.0, "Connecting to YouTube...")
    youtube, client = _get_youtube_client(db_path)
    date_str = datetime.now().strftime("%Y-%m-%d")
    await progress(
        20.0, f"Creating 'Watch Later Export {date_str}'...",
    )
    export_pl = client.create_playlist(
        f"Watch Later Export {date_str}",
        description=f"Exported from Watch Later on {date_str}",
        privacy="private",
    )

    for i, v in enumerate(all_videos):
        vid = v.get("id") or v.get("video_id")
        try:
            client.add_to_playlist(export_pl["id"], vid)
        except Exception:
            pass
        pct = 20 + (i / len(all_videos)) * 20
        await progress(
            pct, f"Adding to export ({i + 1}/{len(all_videos)})",
        )

    await progress(45.0, "Updating Watch Later Archive...")
    playlists = client.list_playlists()
    archive_id = None
    for pl in playlists:
        if pl["snippet"]["title"] == "Watch Later Archive":
            archive_id = pl["id"]
            break
    if not archive_id:
        archive_pl = client.create_playlist(
            "Watch Later Archive", privacy="private",
        )
        archive_id = archive_pl["id"]

    for i, v in enumerate(all_videos):
        vid = v.get("id") or v.get("video_id")
        try:
            client.add_to_playlist(archive_id, vid)
        except Exception:
            pass
        pct = 45 + (i / len(all_videos)) * 20
        await progress(
            pct, f"Archiving ({i + 1}/{len(all_videos)})",
        )

    await progress(70.0, f"Copying unwatched to '{target}'...")
    target_id = None
    for pl in playlists:
        if pl["snippet"]["title"] == target:
            target_id = pl["id"]
            break
    if not target_id:
        target_pl = client.create_playlist(target, privacy="private")
        target_id = target_pl["id"]

    for i, v in enumerate(unwatched):
        vid = v.get("id") or v.get("video_id")
        try:
            client.add_to_playlist(target_id, vid)
        except Exception:
            pass
        if unwatched:
            pct = 70 + (i / len(unwatched)) * 20
            await progress(
                pct,
                f"Copying unwatched ({i + 1}/{len(unwatched)})",
            )

    await progress(92.0, "Removing watched from local DB...")
    watched_ids = [v["id"] for v in watched]
    manager.remove_videos_from_db("WL", watched_ids)
    await progress(
        100.0,
        f"Export complete: {len(all_videos)} exported, "
        f"{len(watched)} removed",
    )


async def handle_purge(params, progress):
    """Purge watched videos from Watch Later via browser automation."""
    import re

    from playwright.async_api import async_playwright

    from youtube_helper.browser.watch_later import find_chrome_profile_path
    from youtube_helper.config.settings import Settings
    from youtube_helper.watch_later.manager import WatchLaterManager

    settings = Settings()
    threshold = params.get("threshold", 50.0)
    headless = params.get("headless", False)
    manager = WatchLaterManager(str(settings.db_path))
    watched = manager.get_watched_videos(threshold=threshold)
    if not watched:
        await progress(100.0, "No watched videos to purge")
        return

    await progress(
        10.0, f"Launching Chrome to remove {len(watched)} videos...",
    )
    chrome_path = find_chrome_profile_path()
    video_ids = {v["id"] for v in watched}

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_path,
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(
            "https://www.youtube.com/playlist?list=WL",
            wait_until="networkidle",
        )
        await page.wait_for_selector(
            "ytd-playlist-video-renderer", timeout=15000,
        )

        for _ in range(50):
            await page.evaluate(
                "window.scrollBy(0, window.innerHeight)",
            )
            await page.wait_for_timeout(500)

        removed = 0
        renderers = await page.query_selector_all(
            "ytd-playlist-video-renderer",
        )
        for renderer in renderers:
            link = await renderer.query_selector("a#thumbnail")
            href = await link.get_attribute("href") if link else ""
            match = re.search(r"v=([^&]+)", href or "")
            if not match:
                continue
            vid = match.group(1)
            if vid in video_ids:
                menu_btn = await renderer.query_selector(
                    "yt-icon-button#button, "
                    "button[aria-label='Action menu']",
                )
                if menu_btn:
                    await menu_btn.click()
                    await page.wait_for_timeout(300)
                    remove_btn = await page.query_selector(
                        "tp-yt-paper-listbox "
                        "ytd-menu-service-item-renderer"
                        ":has-text('Remove from')",
                    )
                    if not remove_btn:
                        remove_btn = await page.query_selector(
                            "ytd-menu-service-item-renderer"
                            ":has-text('Remove')",
                        )
                    if remove_btn:
                        await remove_btn.click()
                        await page.wait_for_timeout(500)
                        removed += 1
                        pct = 10 + (removed / len(video_ids)) * 85
                        await progress(
                            pct,
                            f"Removed {removed}/{len(video_ids)}",
                        )
        await ctx.close()

    manager.remove_videos_from_db(
        "WL", [v["id"] for v in watched],
    )
    await progress(100.0, f"Purged {removed} videos")


async def handle_prune_exports(params, progress):
    """Remove watched videos from export playlists."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    db_path = str(settings.db_path)
    await progress(10.0, "Connecting to YouTube...")
    _, client = _get_youtube_client(db_path)
    playlists = client.list_playlists()
    exports = [
        p for p in playlists
        if p["snippet"]["title"].startswith("Watch Later Export")
    ]
    if not exports:
        await progress(100.0, "No export playlists found")
        return

    total_pruned = 0
    for i, pl in enumerate(exports):
        items = client.list_playlist_items(pl["id"])
        for item in items:
            vid_id = item["snippet"]["resourceId"]["videoId"]
            conn = get_connection(db_path)
            video = conn.execute(
                "SELECT watch_progress FROM videos WHERE id = ?",
                (vid_id,),
            ).fetchone()
            conn.close()
            if video and video["watch_progress"] >= 50.0:
                client.remove_from_playlist(item["id"])
                total_pruned += 1
        pct = 10 + ((i + 1) / len(exports)) * 85
        await progress(
            pct, f"Pruned {pl['snippet']['title']}",
        )
    await progress(
        100.0,
        f"Pruned {total_pruned} watched videos "
        f"from {len(exports)} playlists",
    )


async def handle_create_playlist(params, progress):
    """Create a new YouTube playlist."""
    from youtube_helper.config.settings import Settings

    settings = Settings()
    await progress(30.0, "Creating playlist...")
    _, client = _get_youtube_client(str(settings.db_path))
    client.create_playlist(
        params["title"],
        description=params.get("description", ""),
        privacy=params.get("privacy", "private"),
    )
    await progress(100.0, f"Created '{params['title']}'")


async def handle_delete_playlist(params, progress):
    """Delete a YouTube playlist."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    await progress(30.0, "Deleting playlist...")
    youtube, _ = _get_youtube_client(str(settings.db_path))
    youtube.playlists().delete(id=params["playlist_id"]).execute()
    conn = get_connection(str(settings.db_path))
    conn.execute(
        "UPDATE playlist_videos SET removed_at = datetime('now') "
        "WHERE playlist_id = ? AND removed_at IS NULL",
        (params["playlist_id"],),
    )
    conn.commit()
    # Disable FK checks outside a transaction so we can delete the
    # playlist row while soft-deleted child rows still reference it.
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "DELETE FROM playlists WHERE id = ?",
        (params["playlist_id"],),
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    await progress(100.0, "Playlist deleted")


async def handle_add_videos(params, progress):
    """Add videos to a YouTube playlist."""
    from youtube_helper.config.settings import Settings

    settings = Settings()
    _, client = _get_youtube_client(str(settings.db_path))
    video_ids = params["video_ids"]
    for i, vid in enumerate(video_ids):
        client.add_to_playlist(params["playlist_id"], vid)
        pct = (i + 1) / len(video_ids) * 100
        await progress(pct, f"Added {i + 1}/{len(video_ids)}")


async def handle_remove_video(params, progress):
    """Remove a video from a YouTube playlist."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    db_path = str(settings.db_path)
    _, client = _get_youtube_client(db_path)
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT playlist_item_id FROM playlist_videos "
        "WHERE playlist_id = ? AND video_id = ?",
        (params["playlist_id"], params["video_id"]),
    ).fetchone()
    conn.close()
    if row and row["playlist_item_id"]:
        await progress(50.0, "Removing from YouTube...")
        client.remove_from_playlist(row["playlist_item_id"])
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE playlist_videos SET removed_at = datetime('now') "
        "WHERE playlist_id = ? AND video_id = ? AND removed_at IS NULL",
        (params["playlist_id"], params["video_id"]),
    )
    conn.commit()
    conn.close()
    await progress(100.0, "Video removed")


async def handle_reorder(params, progress):
    """Reorder videos in a playlist (local DB only)."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    db_path = str(settings.db_path)
    conn = get_connection(db_path)
    for i, vid in enumerate(params["video_ids"]):
        conn.execute(
            "UPDATE playlist_videos SET position = ? "
            "WHERE playlist_id = ? AND video_id = ?",
            (i, params["playlist_id"], vid),
        )
    conn.commit()
    conn.close()
    await progress(100.0, "Reorder saved")


async def handle_like(params, progress):
    """Like a YouTube video."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    await progress(50.0, "Liking video...")
    youtube.videos().rate(
        id=params["video_id"], rating="like",
    ).execute()
    conn = get_connection(str(settings.db_path))
    conn.execute(
        "INSERT INTO liked_videos (video_id, liked_at) "
        "VALUES (?, datetime('now')) "
        "ON CONFLICT(video_id) DO UPDATE SET liked_at=datetime('now'), removed_at=NULL",
        (params["video_id"],),
    )
    conn.commit()
    conn.close()
    await progress(100.0, "Video liked")


async def handle_unlike(params, progress):
    """Remove like from a YouTube video."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    await progress(50.0, "Removing like...")
    youtube.videos().rate(
        id=params["video_id"], rating="none",
    ).execute()
    conn = get_connection(str(settings.db_path))
    conn.execute(
        "UPDATE liked_videos SET removed_at = datetime('now') "
        "WHERE video_id = ? AND removed_at IS NULL",
        (params["video_id"],),
    )
    conn.commit()
    conn.close()
    await progress(100.0, "Like removed")
