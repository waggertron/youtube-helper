from fastapi import APIRouter, Request

from youtube_helper.db.connection import get_connection

router = APIRouter(prefix="/api", tags=["system"])


@router.post("/reset", status_code=200)
async def reset_database(request: Request):
    """Clear all data from the local database. Does not affect YouTube."""
    conn = get_connection(request.app.state.db_path)
    # Delete from child tables first (foreign key constraints)
    conn.execute("DELETE FROM playlist_videos")
    conn.execute("DELETE FROM liked_videos")
    conn.execute("DELETE FROM downloads")
    # Delete from parent tables
    conn.execute("DELETE FROM playlists")
    conn.execute("DELETE FROM videos")
    # Delete queue and watch history
    conn.execute("DELETE FROM operation_queue")
    conn.execute("DELETE FROM watch_history")
    conn.commit()
    conn.close()
    return {"message": "Database cleared"}
