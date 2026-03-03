# src/youtube_helper/web/routes/queue.py
from fastapi import APIRouter, HTTPException, Request

from youtube_helper.web.queue import QueueManager

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("")
async def list_queue(request: Request):
    qm = QueueManager(request.app.state.db_path)
    return {"operations": qm.list_operations()}


@router.delete("/{op_id}")
async def cancel_operation(op_id: int, request: Request):
    qm = QueueManager(request.app.state.db_path)
    if not qm.cancel_operation(op_id):
        raise HTTPException(400, "Can only cancel pending operations")
    return {"message": "Operation cancelled"}


@router.post("/{op_id}/retry")
async def retry_operation(op_id: int, request: Request):
    qm = QueueManager(request.app.state.db_path)
    op = qm.get_operation(op_id)
    if not op or op["status"] != "failed":
        raise HTTPException(400, "Can only retry failed operations")
    qm.update_operation(op_id, status="pending", progress=0.0, error="", message="")
    return {"message": "Operation requeued"}


@router.post("/{op_id}/skip")
async def skip_operation(op_id: int, request: Request):
    qm = QueueManager(request.app.state.db_path)
    op = qm.get_operation(op_id)
    if not op or op["status"] != "failed":
        raise HTTPException(400, "Can only skip failed operations")
    qm.update_operation(op_id, status="skipped")
    return {"message": "Operation skipped"}
