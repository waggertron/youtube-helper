from fastapi import APIRouter, Request

router = APIRouter(tags=["sync"])


@router.post("/api/sync", status_code=202)
async def sync(request: Request):
    from youtube_helper.web.handlers import handle_sync

    bg = request.app.state.bg_tasks
    bg.start("sync", handle_sync)
    return {"status": "running", "message": "Sync started"}


@router.get("/api/sync/status")
async def sync_status(request: Request):
    bg = request.app.state.bg_tasks
    status = bg.get_status("sync")
    if status is None:
        return {"status": "idle"}
    return status
