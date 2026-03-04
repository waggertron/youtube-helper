from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from youtube_helper.db.connection import get_connection

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class CreatePlaylistRequest(BaseModel):
    title: str
    description: str = ""
    privacy: str = "private"


class AddVideosRequest(BaseModel):
    video_ids: list[str]


class ReorderRequest(BaseModel):
    video_ids: list[str]


@router.get("")
async def list_playlists(request: Request):
    conn = get_connection(request.app.state.db_path)
    rows = conn.execute("SELECT * FROM playlists ORDER BY title").fetchall()
    conn.close()
    return {"playlists": [dict(r) for r in rows]}


@router.get("/{playlist_id}/videos")
async def get_playlist_videos(playlist_id: str, request: Request):
    conn = get_connection(request.app.state.db_path)
    playlist = conn.execute(
        "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
    ).fetchone()
    if not playlist:
        conn.close()
        raise HTTPException(status_code=404, detail="Playlist not found")
    rows = conn.execute(
        """SELECT v.*, pv.position,
           (SELECT 1 FROM liked_videos lv
            WHERE lv.video_id = v.id AND lv.removed_at IS NULL) as is_liked
           FROM videos v
           JOIN playlist_videos pv ON v.id = pv.video_id
           WHERE pv.playlist_id = ? AND pv.removed_at IS NULL
           ORDER BY pv.position""",
        (playlist_id,),
    ).fetchall()
    conn.close()
    return {"playlist": dict(playlist), "videos": [dict(r) for r in rows]}


@router.post("", status_code=202)
async def create_playlist(body: CreatePlaylistRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("create_playlist", body.model_dump())
    return {"operation_id": op_id, "message": "Create playlist queued"}


@router.delete("/{playlist_id}", status_code=202)
async def delete_playlist(playlist_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("delete_playlist", {"playlist_id": playlist_id})
    return {"operation_id": op_id, "message": "Delete playlist queued"}


@router.post("/{playlist_id}/videos", status_code=202)
async def add_videos(playlist_id: str, body: AddVideosRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit(
        "add_videos", {"playlist_id": playlist_id, "video_ids": body.video_ids}
    )
    return {"operation_id": op_id, "message": "Add videos queued"}


@router.delete("/{playlist_id}/videos/{video_id}", status_code=202)
async def remove_video(playlist_id: str, video_id: str, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit(
        "remove_video", {"playlist_id": playlist_id, "video_id": video_id}
    )
    return {"operation_id": op_id, "message": "Remove video queued"}


@router.put("/{playlist_id}/reorder", status_code=202)
async def reorder_playlist(
    playlist_id: str, body: ReorderRequest, request: Request
):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit(
        "reorder_playlist",
        {"playlist_id": playlist_id, "video_ids": body.video_ids},
    )
    return {"operation_id": op_id, "message": "Reorder queued"}
