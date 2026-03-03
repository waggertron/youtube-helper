from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app(db_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    from youtube_helper.config.settings import Settings

    settings = Settings()
    resolved_db_path = db_path or str(settings.db_path)

    app = FastAPI(title="YouTube Helper", version="0.1.0")

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
    from youtube_helper.web.routes.search import router as search_router
    from youtube_helper.web.routes.sync import router as sync_router

    app.state.broadcaster = EventBroadcaster()
    app.include_router(auth_router)
    app.include_router(events_router)
    app.include_router(search_router)
    app.include_router(sync_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app
