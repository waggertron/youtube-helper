# src/youtube_helper/web/routes/watch_later.py
from fastapi import APIRouter, File, Query, Request, UploadFile
from pydantic import BaseModel

from youtube_helper.db.connection import get_connection
from youtube_helper.takeout import parse_takeout_watch_later
from youtube_helper.web.handlers import handle_export

router = APIRouter(prefix="/api/watch-later", tags=["watch-later"])


class ExportRequest(BaseModel):
    target: str = "spacepope videos"
    threshold: float = 50.0


class PurgeRequest(BaseModel):
    threshold: float = 50.0
    headless: bool = True


@router.get("")
async def list_watch_later(request: Request):
    from youtube_helper.watch_later.manager import WatchLaterManager
    manager = WatchLaterManager(request.app.state.db_path)
    videos = manager.export_playlist_data("WL")
    return {"videos": videos}


@router.get("/watched")
async def watched_videos(
    request: Request, threshold: float = Query(50.0, ge=0, le=100)
):
    from youtube_helper.watch_later.manager import WatchLaterManager
    manager = WatchLaterManager(request.app.state.db_path)
    videos = manager.get_watched_videos(threshold=threshold)
    return {"videos": videos, "threshold": threshold}


@router.get("/unwatched")
async def unwatched_videos(
    request: Request, threshold: float = Query(50.0, ge=0, le=100)
):
    from youtube_helper.watch_later.manager import WatchLaterManager
    manager = WatchLaterManager(request.app.state.db_path)
    videos = manager.get_unwatched_videos(threshold=threshold)
    return {"videos": videos, "threshold": threshold}


@router.post("/import")
async def import_watch_later(request: Request, file: UploadFile = File(...)):
    """Import Watch Later videos from a Google Takeout export file."""
    data = await file.read()
    videos = parse_takeout_watch_later(data)
    if not videos:
        return {"imported": 0, "total_parsed": 0}

    db_path = request.app.state.db_path
    conn = get_connection(db_path)

    # Ensure WL playlist exists
    conn.execute(
        "INSERT OR IGNORE INTO playlists (id, title, source) VALUES ('WL', 'Watch Later', 'takeout')"
    )

    imported = 0
    for v in videos:
        conn.execute(
            "INSERT INTO videos (id, title) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET title = excluded.title",
            (v["video_id"], v.get("title", "")),
        )
        conn.execute(
            "INSERT INTO playlist_videos (playlist_id, video_id, position) "
            "VALUES ('WL', ?, ?) "
            "ON CONFLICT(playlist_id, video_id) DO NOTHING",
            (v["video_id"], imported),
        )
        imported += 1

    conn.commit()
    conn.close()
    return {"imported": imported, "total_parsed": len(videos)}


@router.post("/export")
async def export_watch_later(body: ExportRequest):
    """Export Watch Later videos to a YouTube playlist."""
    result = await handle_export(target=body.target, threshold=body.threshold)
    return result


@router.post("/purge", status_code=202)
async def purge_watch_later(request: Request, body: PurgeRequest):
    """Remove exported videos from Watch Later via browser automation."""
    from youtube_helper.browser.watch_later import purge_videos_from_watch_later
    from youtube_helper.watch_later.manager import WatchLaterManager

    manager = WatchLaterManager(request.app.state.db_path)
    # Get videos that have been exported (watched videos based on threshold)
    watched = manager.get_watched_videos(threshold=body.threshold)
    if not watched:
        return {"status": "completed", "message": "No videos to purge", "removed": 0}

    video_ids = [v["id"] for v in watched]
    bg = request.app.state.bg_tasks

    async def job(update):
        result = await purge_videos_from_watch_later(
            video_ids=video_ids, update=update, headless=body.headless
        )
        # Soft-delete purged videos from local DB
        conn = get_connection(request.app.state.db_path)
        for vid in video_ids[:result.get("removed", 0)]:
            conn.execute(
                "UPDATE playlist_videos SET removed_at = datetime('now') "
                "WHERE playlist_id = 'WL' AND video_id = ? AND removed_at IS NULL",
                (vid,),
            )
        conn.commit()
        conn.close()

    bg.start("purge", job)
    return {"status": "running", "message": f"Purging {len(video_ids)} videos", "total": len(video_ids)}


@router.get("/purge/status")
async def purge_status(request: Request):
    bg = request.app.state.bg_tasks
    status = bg.get_status("purge")
    if status is None:
        return {"status": "idle"}
    return status
