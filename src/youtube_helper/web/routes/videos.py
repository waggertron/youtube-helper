# src/youtube_helper/web/routes/videos.py
from fastapi import APIRouter, Request

from youtube_helper.db.connection import get_connection
from youtube_helper.web.handlers import handle_like, handle_unlike

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("")
async def list_all_videos(request: Request):
    conn = get_connection(request.app.state.db_path)
    rows = conn.execute(
        """SELECT v.*,
           GROUP_CONCAT(DISTINCT p.title) as playlist_names,
           GROUP_CONCAT(DISTINCT p.id) as playlist_ids,
           (SELECT 1 FROM liked_videos lv
            WHERE lv.video_id = v.id AND lv.removed_at IS NULL) as is_liked
           FROM videos v
           LEFT JOIN playlist_videos pv ON v.id = pv.video_id AND pv.removed_at IS NULL
           LEFT JOIN playlists p ON pv.playlist_id = p.id
           GROUP BY v.id
           ORDER BY v.title"""
    ).fetchall()
    conn.close()
    return {"videos": [dict(r) for r in rows]}


@router.get("/liked")
async def list_liked(request: Request):
    conn = get_connection(request.app.state.db_path)
    rows = conn.execute(
        """SELECT v.*, lv.liked_at FROM videos v
           JOIN liked_videos lv ON v.id = lv.video_id
           WHERE lv.removed_at IS NULL
           ORDER BY lv.liked_at DESC"""
    ).fetchall()
    conn.close()
    return {"videos": [dict(r) for r in rows]}


@router.post("/{video_id}/like")
async def like_video(video_id: str):
    result = await handle_like(video_id=video_id)
    return result


@router.delete("/{video_id}/like")
async def unlike_video(video_id: str):
    result = await handle_unlike(video_id=video_id)
    return result
