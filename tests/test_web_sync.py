# tests/test_web_sync.py
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def app(db_path):
    return create_app(db_path=db_path)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestSyncRoutes:
    @pytest.mark.asyncio
    async def test_sync_returns_202(self, client):
        with patch(
            "youtube_helper.web.handlers.handle_sync", new_callable=AsyncMock
        ):
            resp = await client.post("/api/sync")
            assert resp.status_code == 202
            assert resp.json()["status"] == "running"

    @pytest.mark.asyncio
    async def test_sync_status_idle(self, client):
        resp = await client.get("/api/sync/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "idle"
