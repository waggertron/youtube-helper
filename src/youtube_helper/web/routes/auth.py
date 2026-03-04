import json
import pickle

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from youtube_helper.api.auth import SCOPES
from youtube_helper.config.settings import Settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_settings(request: Request) -> Settings:
    """Return settings from app state if available, otherwise create default."""
    return getattr(request.app.state, "settings", None) or Settings()


@router.get("/status")
async def auth_status(request: Request):
    settings = _get_settings(request)
    return {
        "authenticated": settings.token_path.exists(),
        "has_client_secret": settings.client_secret_path.exists(),
        "has_token": settings.token_path.exists(),
        "config_dir": str(settings.config_dir),
    }


@router.post("/upload-secret")
async def upload_client_secret(request: Request, file: UploadFile = File(...)):
    settings = _get_settings(request)
    content = await file.read()
    try:
        data = json.loads(content)
        if "installed" not in data and "web" not in data:
            raise ValueError(
                "Invalid client secret format — expected 'installed' or 'web' key"
            )
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    settings.ensure_dirs()
    settings.client_secret_path.write_bytes(content)
    return {"message": "Client secret saved"}


@router.get("/start")
async def start_auth(request: Request):
    settings = _get_settings(request)
    if not settings.client_secret_path.exists():
        raise HTTPException(status_code=400, detail="Upload client_secret.json first")

    flow = Flow.from_client_secrets_file(
        str(settings.client_secret_path),
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/auth/callback",
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    request.app.state.oauth_state = state
    return {"auth_url": auth_url}


@router.get("/callback")
async def auth_callback(code: str, state: str, request: Request):
    settings = _get_settings(request)
    flow = Flow.from_client_secrets_file(
        str(settings.client_secret_path),
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/auth/callback",
        state=state,
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    settings.ensure_dirs()
    with open(settings.token_path, "wb") as f:
        pickle.dump(credentials, f)
    return RedirectResponse(url="/settings?auth=success")
