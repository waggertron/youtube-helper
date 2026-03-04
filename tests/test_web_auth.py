# tests/test_web_auth.py
import json
import pickle
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.config.settings import Settings
from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def config_dir(tmp_path):
    """Provide a temporary config directory for auth tests."""
    return tmp_path / "config"


@pytest.fixture
def app(tmp_path, config_dir):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    application = create_app(db_path=db_path)
    # Store settings with temp config dir on app.state so routes can use it
    application.state.settings = Settings(config_dir=config_dir)
    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def valid_client_secret():
    return json.dumps({
        "installed": {
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }).encode()


@pytest.fixture
def web_client_secret():
    return json.dumps({
        "web": {
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }).encode()


class TestUploadClientSecret:
    @pytest.mark.asyncio
    async def test_upload_valid_client_secret(self, client, valid_client_secret, config_dir):
        resp = await client.post(
            "/api/auth/upload-secret",
            files={"file": ("client_secret.json", valid_client_secret, "application/json")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Client secret saved"
        # Verify file was actually written
        saved = config_dir / "client_secret.json"
        assert saved.exists()
        assert json.loads(saved.read_bytes())["installed"]["client_id"] == "test-client-id.apps.googleusercontent.com"

    @pytest.mark.asyncio
    async def test_upload_web_client_secret(self, client, web_client_secret, config_dir):
        resp = await client.post(
            "/api/auth/upload-secret",
            files={"file": ("client_secret.json", web_client_secret, "application/json")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Client secret saved"

    @pytest.mark.asyncio
    async def test_upload_invalid_json(self, client):
        resp = await client.post(
            "/api/auth/upload-secret",
            files={"file": ("client_secret.json", b"not valid json", "application/json")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_missing_key(self, client):
        content = json.dumps({"wrong_key": "value"}).encode()
        resp = await client.post(
            "/api/auth/upload-secret",
            files={"file": ("client_secret.json", content, "application/json")},
        )
        assert resp.status_code == 400
        assert "installed" in resp.json()["detail"] or "web" in resp.json()["detail"]


class TestStartAuth:
    @pytest.mark.asyncio
    async def test_start_auth_no_secret(self, client):
        resp = await client.get("/api/auth/start")
        assert resp.status_code == 400
        assert "Upload client_secret.json first" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_auth_returns_url(self, client, valid_client_secret, config_dir):
        # Seed the client secret file
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "client_secret.json").write_bytes(valid_client_secret)

        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=test",
            "test-state-123",
        )

        with patch("youtube_helper.web.routes.auth.Flow") as MockFlow:
            MockFlow.from_client_secrets_file.return_value = mock_flow
            resp = await client.get("/api/auth/start")

        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert data["auth_url"].startswith("https://accounts.google.com")

        # Verify Flow was created with correct params
        MockFlow.from_client_secrets_file.assert_called_once()
        call_args = MockFlow.from_client_secrets_file.call_args
        assert call_args[1]["redirect_uri"] == "http://localhost:8000/api/auth/callback"

        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline", prompt="consent",
        )


class _FakeCredentials:
    """A picklable stand-in for google.oauth2.credentials.Credentials."""

    def __init__(self, token, refresh_token):
        self.token = token
        self.refresh_token = refresh_token


class TestAuthCallback:
    @pytest.mark.asyncio
    async def test_auth_callback(self, client, valid_client_secret, config_dir, app):
        # Seed the client secret file
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "client_secret.json").write_bytes(valid_client_secret)

        # Set up app state with oauth_state
        app.state.oauth_state = "test-state-123"

        fake_credentials = _FakeCredentials(
            token="fake-token", refresh_token="fake-refresh-token"
        )

        mock_flow = MagicMock()
        mock_flow.credentials = fake_credentials

        with patch("youtube_helper.web.routes.auth.Flow") as MockFlow:
            MockFlow.from_client_secrets_file.return_value = mock_flow
            resp = await client.get(
                "/api/auth/callback",
                params={"code": "auth-code-123", "state": "test-state-123"},
                follow_redirects=False,
            )

        # Should redirect to /settings?auth=success
        assert resp.status_code == 307
        assert "/settings?auth=success" in resp.headers["location"]

        # Verify token was saved
        token_path = config_dir / "token.pickle"
        assert token_path.exists()
        with open(token_path, "rb") as f:
            saved_creds = pickle.load(f)  # noqa: S301
        assert saved_creds.token == "fake-token"

        # Verify flow was used correctly
        mock_flow.fetch_token.assert_called_once_with(code="auth-code-123")
