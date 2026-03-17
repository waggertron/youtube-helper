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
    app.state.settings = settings

    from youtube_helper.web.tasks import BackgroundTasks

    app.state.bg_tasks = BackgroundTasks()

    from youtube_helper.web.routes.auth import router as auth_router
    from youtube_helper.web.routes.playlists import router as playlists_router
    from youtube_helper.web.routes.search import router as search_router
    from youtube_helper.web.routes.sync import router as sync_router
    from youtube_helper.web.routes.system import router as system_router
    from youtube_helper.web.routes.videos import router as videos_router
    from youtube_helper.web.routes.watch_later import router as watch_later_router

    app.include_router(auth_router)
    app.include_router(playlists_router)
    app.include_router(search_router)
    app.include_router(sync_router)
    app.include_router(system_router)
    app.include_router(videos_router)
    app.include_router(watch_later_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    # Serve built frontend static files in production
    from pathlib import Path

    frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = (frontend_dist / full_path).resolve()
            if file_path.is_relative_to(frontend_dist) and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_dist / "index.html")

    return app
