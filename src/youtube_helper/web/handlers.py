"""Operation handlers for web routes.

Each handler is an async function with named parameters that returns a result dict.
Slow handlers (sync, purge) accept an `update` callback from BackgroundTasks.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("youtube_helper.handlers")


def _get_youtube_client(db_path: str):
    """Create an authenticated YouTube client and PlaylistClient."""
    logger.info("Creating authenticated YouTube client")
    from youtube_helper.api.auth import get_authenticated_service
    from youtube_helper.api.playlists import PlaylistClient
    from youtube_helper.config.settings import Settings

    settings = Settings()
    youtube = get_authenticated_service(settings)
    return youtube, PlaylistClient(youtube)


async def handle_sync(update) -> None:
    """Sync all playlists from YouTube.

    Args:
        update: Callback from BackgroundTasks - update(progress=50, message="...")
    """
    logger.info("Starting sync operation")
    from youtube_helper.config.settings import Settings
    from youtube_helper.sync.engine import SyncEngine

    settings = Settings()
    db_path = str(settings.db_path)
    update(progress=10, message="Connecting to YouTube...")
    _, client = _get_youtube_client(db_path)
    update(progress=20, message="Syncing playlists...")
    engine = SyncEngine(db_path, client)
    stats = engine.sync_all()
    update(progress=85, message="Syncing liked videos...")
    liked_count = engine.sync_liked_videos()
    update(
        progress=100,
        message=f"Synced {stats['playlists']} playlists, {stats['videos']} videos, "
        f"{liked_count} liked videos",
    )


async def handle_export(target: str, threshold: float = 50.0) -> dict:
    """Export Watch Later playlist to YouTube playlists.

    Returns:
        {"exported": count, "playlist_id": id}
    """
    from datetime import datetime

    from youtube_helper.config.settings import Settings
    from youtube_helper.watch_later.manager import WatchLaterManager

    settings = Settings()
    db_path = str(settings.db_path)
    manager = WatchLaterManager(db_path)
    all_videos = manager.export_playlist_data("WL")
    watched = manager.get_watched_videos(threshold=threshold)
    unwatched = manager.get_unwatched_videos(threshold=threshold)

    if not all_videos:
        return {"exported": 0, "playlist_id": None}

    youtube, client = _get_youtube_client(db_path)
    date_str = datetime.now().strftime("%Y-%m-%d")
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

    watched_ids = [v["id"] for v in watched]
    manager.remove_videos_from_db("WL", watched_ids)
    return {"exported": len(all_videos), "playlist_id": export_pl["id"]}


async def handle_create_playlist(
    title: str, description: str = "", privacy: str = "private",
) -> dict:
    """Create a new YouTube playlist."""
    from youtube_helper.config.settings import Settings

    settings = Settings()
    _, client = _get_youtube_client(str(settings.db_path))
    result = client.create_playlist(
        title, description=description, privacy=privacy,
    )
    return result


async def handle_delete_playlist(playlist_id: str) -> dict:
    """Delete a YouTube playlist."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    youtube.playlists().delete(id=playlist_id).execute()
    conn = get_connection(str(settings.db_path))
    conn.execute(
        "UPDATE playlist_videos SET removed_at = datetime('now') "
        "WHERE playlist_id = ? AND removed_at IS NULL",
        (playlist_id,),
    )
    conn.commit()
    # Disable FK checks outside a transaction so we can delete the
    # playlist row while soft-deleted child rows still reference it.
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "DELETE FROM playlists WHERE id = ?",
        (playlist_id,),
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    return {"deleted": playlist_id}


async def handle_add_videos(playlist_id: str, video_ids: list[str]) -> dict:
    """Add videos to a YouTube playlist."""
    from youtube_helper.config.settings import Settings

    settings = Settings()
    _, client = _get_youtube_client(str(settings.db_path))
    for vid in video_ids:
        client.add_to_playlist(playlist_id, vid)
    return {"added": len(video_ids)}


async def handle_remove_video(playlist_id: str, video_id: str) -> dict:
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
        (playlist_id, video_id),
    ).fetchone()
    conn.close()
    if row and row["playlist_item_id"]:
        client.remove_from_playlist(row["playlist_item_id"])
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE playlist_videos SET removed_at = datetime('now') "
        "WHERE playlist_id = ? AND video_id = ? AND removed_at IS NULL",
        (playlist_id, video_id),
    )
    conn.commit()
    conn.close()
    return {"removed": video_id}


async def handle_reorder(playlist_id: str, video_ids: list[str]) -> dict:
    """Reorder videos in a playlist (local DB only)."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    db_path = str(settings.db_path)
    conn = get_connection(db_path)
    for i, vid in enumerate(video_ids):
        conn.execute(
            "UPDATE playlist_videos SET position = ? "
            "WHERE playlist_id = ? AND video_id = ?",
            (i, playlist_id, vid),
        )
    conn.commit()
    conn.close()
    return {"reordered": True}


async def handle_like(video_id: str) -> dict:
    """Like a YouTube video."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    youtube.videos().rate(
        id=video_id, rating="like",
    ).execute()
    conn = get_connection(str(settings.db_path))
    conn.execute(
        "INSERT INTO liked_videos (video_id, liked_at) "
        "VALUES (?, datetime('now')) "
        "ON CONFLICT(video_id) DO UPDATE SET liked_at=datetime('now'), removed_at=NULL",
        (video_id,),
    )
    conn.commit()
    conn.close()
    return {"video_id": video_id, "status": "liked"}


async def handle_unlike(video_id: str) -> dict:
    """Remove like from a YouTube video."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    youtube.videos().rate(
        id=video_id, rating="none",
    ).execute()
    conn = get_connection(str(settings.db_path))
    conn.execute(
        "UPDATE liked_videos SET removed_at = datetime('now') "
        "WHERE video_id = ? AND removed_at IS NULL",
        (video_id,),
    )
    conn.commit()
    conn.close()
    return {"video_id": video_id, "status": "unliked"}


async def handle_like_all(video_ids: list[str]) -> dict:
    """Like all specified videos."""
    from youtube_helper.config.settings import Settings
    from youtube_helper.db.connection import get_connection

    settings = Settings()
    youtube, _ = _get_youtube_client(str(settings.db_path))
    for vid in video_ids:
        youtube.videos().rate(id=vid, rating="like").execute()
        conn = get_connection(str(settings.db_path))
        conn.execute(
            "INSERT INTO liked_videos (video_id, liked_at) "
            "VALUES (?, datetime('now')) "
            "ON CONFLICT(video_id) DO UPDATE SET liked_at=datetime('now'), removed_at=NULL",
            (vid,),
        )
        conn.commit()
        conn.close()
    return {"liked": len(video_ids)}
