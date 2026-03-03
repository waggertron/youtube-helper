# src/youtube_helper/web/routes/videos.py
from fastapi import APIRouter, Request

from youtube_helper.db.connection import get_connection

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("/liked")
async def list_liked(request: Request):
    conn = get_connection(request.app.state.db_path)
    rows = conn.execute(
        """SELECT v.*, lv.liked_at FROM videos v
           JOIN liked_videos lv ON v.id = lv.video_id
           ORDER BY lv.liked_at DESC"""
    ).fetchall()
    conn.close()
    return {"videos": [dict(r) for r in rows]}


@router.post("/{video_id}/like", status_code=202)
async def like_video(video_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("like_video", {"video_id": video_id})
    return {"operation_id": op_id, "message": "Like queued"}


@router.delete("/{video_id}/like", status_code=202)
async def unlike_video(video_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("unlike_video", {"video_id": video_id})
    return {"operation_id": op_id, "message": "Unlike queued"}
