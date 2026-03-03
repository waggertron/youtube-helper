from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["sync"])


@router.post("/sync", status_code=202)
async def trigger_sync(request: Request):
    from youtube_helper.web.queue import QueueManager

    qm = QueueManager(request.app.state.db_path)
    op_id = qm.submit("sync", {})
    return {"operation_id": op_id, "message": "Sync queued"}
