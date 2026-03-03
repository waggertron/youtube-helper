import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.web.app import create_app


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.db")
    from youtube_helper.db.migrations import run_migrations

    run_migrations(db_path)
    return create_app(db_path=db_path)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_includes_version(self, client):
        resp = await client.get("/api/health")
        data = resp.json()
        assert "version" in data
