# tests/test_web_routes_basic.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.db")
    run_migrations(db_path)
    return create_app(db_path=db_path)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAuthRoutes:
    @pytest.mark.asyncio
    async def test_auth_status(self, client):
        resp = await client.get("/api/auth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "authenticated" in data
        assert "has_client_secret" in data
        assert "has_token" in data


class TestSearchRoutes:
    @pytest.mark.asyncio
    async def test_search_empty_db(self, client):
        resp = await client.get("/api/search", params={"q": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_search_requires_query(self, client):
        resp = await client.get("/api/search")
        assert resp.status_code == 422


class TestSyncRoutes:
    @pytest.mark.asyncio
    async def test_sync_submits_to_queue(self, client):
        resp = await client.post("/api/sync")
        assert resp.status_code == 202
        data = resp.json()
        assert "operation_id" in data
        assert data["message"] == "Sync queued"
