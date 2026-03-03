from fastapi import APIRouter, Request

from youtube_helper.config.settings import Settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def auth_status(request: Request):
    settings = Settings()
    return {
        "authenticated": settings.token_path.exists(),
        "has_client_secret": settings.client_secret_path.exists(),
        "has_token": settings.token_path.exists(),
        "config_dir": str(settings.config_dir),
    }
