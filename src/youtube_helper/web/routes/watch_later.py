# src/youtube_helper/web/routes/watch_later.py
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/watch-later", tags=["watch-later"])


class ExportRequest(BaseModel):
    target: str = "spacepope videos"
    threshold: float = 50.0


class PurgeRequest(BaseModel):
    threshold: float = 50.0
    headless: bool = False


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


@router.post("/scrape", status_code=202)
async def scrape_watch_later(request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("scrape_watch_later", {})
    return {"operation_id": op_id, "message": "Scrape queued"}


@router.post("/export", status_code=202)
async def export_watch_later(body: ExportRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("export_watch_later", body.model_dump())
    return {"operation_id": op_id, "message": "Export queued"}


@router.post("/purge", status_code=202)
async def purge_watch_later(body: PurgeRequest, request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("purge_watch_later", body.model_dump())
    return {"operation_id": op_id, "message": "Purge queued"}


@router.post("/prune-exports", status_code=202)
async def prune_exports(request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("prune_exports", {})
    return {"operation_id": op_id, "message": "Prune queued"}
