import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app(db_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    from youtube_helper.config.settings import Settings

    settings = Settings()
    resolved_db_path = db_path or str(settings.db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from youtube_helper.web.handlers import register_all_handlers
        from youtube_helper.web.processor import QueueProcessor

        processor = QueueProcessor(app.state.db_path, app.state.broadcaster)
        register_all_handlers(processor)
        app.state.processor = processor
        task = asyncio.create_task(processor.run())
        yield
        processor.stop()
        task.cancel()

    app = FastAPI(title="YouTube Helper", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.db_path = resolved_db_path

    from youtube_helper.web.events import EventBroadcaster
    from youtube_helper.web.routes.auth import router as auth_router
    from youtube_helper.web.routes.events import router as events_router
    from youtube_helper.web.routes.playlists import router as playlists_router
    from youtube_helper.web.routes.queue import router as queue_router
    from youtube_helper.web.routes.search import router as search_router
    from youtube_helper.web.routes.sync import router as sync_router
    from youtube_helper.web.routes.videos import router as videos_router
    from youtube_helper.web.routes.watch_later import router as watch_later_router

    app.state.broadcaster = EventBroadcaster()
    app.include_router(auth_router)
    app.include_router(events_router)
    app.include_router(playlists_router)
    app.include_router(queue_router)
    app.include_router(search_router)
    app.include_router(sync_router)
    app.include_router(videos_router)
    app.include_router(watch_later_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app
