from __future__ import annotations

import pickle

from youtube_helper.config.settings import Settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_authenticated_service(settings: Settings):
    """Build and return an authenticated YouTube API service."""
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials = None
    if settings.token_path.exists():
        with open(settings.token_path, "rb") as token:
            credentials = pickle.load(token)  # noqa: S301

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not settings.client_secret_path.exists():
                raise FileNotFoundError(
                    f"Client secret not found at {settings.client_secret_path}. "
                    "Run 'yt auth setup' first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(settings.client_secret_path),
                scopes=SCOPES,
            )
            credentials = flow.run_local_server(
                port=8080,
                access_type="offline",
                prompt="consent",
            )

        settings.ensure_dirs()
        with open(settings.token_path, "wb") as token:
            pickle.dump(credentials, token)

    return build("youtube", "v3", credentials=credentials)
