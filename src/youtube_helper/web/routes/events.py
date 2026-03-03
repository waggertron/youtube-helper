from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
async def event_stream(request: Request):
    broadcaster = request.app.state.broadcaster

    async def generate():
        async for event in broadcaster.subscribe():
            if await request.is_disconnected():
                break
            yield {"data": broadcaster.serialize(event)}

    return EventSourceResponse(generate())
