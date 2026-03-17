from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from youtube_helper.db.connection import get_connection
from youtube_helper.web.handlers import (
    handle_add_videos,
    handle_create_playlist,
    handle_delete_playlist,
    handle_like_all,
    handle_remove_video,
    handle_reorder,
)

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


@router.post("")
async def create_playlist(body: CreatePlaylistRequest):
    result = await handle_create_playlist(
        title=body.title, description=body.description, privacy=body.privacy
    )
    return result


@router.delete("/{playlist_id}")
async def delete_playlist(playlist_id: str):
    result = await handle_delete_playlist(playlist_id=playlist_id)
    return result


@router.post("/{playlist_id}/videos")
async def add_videos(playlist_id: str, body: AddVideosRequest):
    result = await handle_add_videos(playlist_id=playlist_id, video_ids=body.video_ids)
    return result


@router.delete("/{playlist_id}/videos/{video_id}")
async def remove_video(playlist_id: str, video_id: str):
    result = await handle_remove_video(playlist_id=playlist_id, video_id=video_id)
    return result


@router.put("/{playlist_id}/reorder")
async def reorder_playlist(playlist_id: str, body: ReorderRequest):
    result = await handle_reorder(playlist_id=playlist_id, video_ids=body.video_ids)
    return result


@router.post("/{playlist_id}/like-all")
async def like_all_videos(playlist_id: str, request: Request):
    conn = get_connection(request.app.state.db_path)
    rows = conn.execute(
        """SELECT pv.video_id FROM playlist_videos pv
           LEFT JOIN liked_videos lv ON pv.video_id = lv.video_id AND lv.removed_at IS NULL
           WHERE pv.playlist_id = ? AND pv.removed_at IS NULL AND lv.video_id IS NULL""",
        (playlist_id,),
    ).fetchall()
    conn.close()
    video_ids = [r["video_id"] for r in rows]
    if not video_ids:
        return {"message": "All videos already liked"}
    result = await handle_like_all(video_ids=video_ids)
    return result
