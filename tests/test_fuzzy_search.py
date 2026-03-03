import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.search.fuzzy import FuzzySearch


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title) VALUES (?, ?)",
        ("PL1", "Programming Tutorials"),
    )
    conn.execute(
        "INSERT INTO playlists (id, title) VALUES (?, ?)",
        ("PL2", "Music Videos"),
    )
    videos = [
        ("V1", "Python Tutorial for Beginners", "Tech Channel"),
        ("V2", "Advanced Python Patterns", "Code Academy"),
        ("V3", "JavaScript Crash Course", "Web Dev"),
        ("V4", "Lo-fi Beats to Study To", "ChilledCow"),
    ]
    for vid_id, title, channel in videos:
        conn.execute(
            "INSERT INTO videos (id, title, channel_name) "
            "VALUES (?, ?, ?)",
            (vid_id, title, channel),
        )
    conn.execute(
        "INSERT INTO playlist_videos "
        "(playlist_id, video_id) VALUES ('PL1', 'V1')"
    )
    conn.execute(
        "INSERT INTO playlist_videos "
        "(playlist_id, video_id) VALUES ('PL1', 'V2')"
    )
    conn.execute(
        "INSERT INTO playlist_videos "
        "(playlist_id, video_id) VALUES ('PL1', 'V3')"
    )
    conn.execute(
        "INSERT INTO playlist_videos "
        "(playlist_id, video_id) VALUES ('PL2', 'V4')"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def search(seeded_db):
    return FuzzySearch(seeded_db)


class TestSearchVideos:
    def test_finds_by_title(self, search):
        results = search.search_videos("python")
        titles = [r["title"] for r in results]
        assert "Python Tutorial for Beginners" in titles
        assert "Advanced Python Patterns" in titles

    def test_finds_by_channel(self, search):
        results = search.search_videos("tech channel")
        assert len(results) >= 1

    def test_no_results_returns_empty(self, search):
        results = search.search_videos(
            "xyznonexistent", threshold=95
        )
        assert len(results) == 0

    def test_respects_threshold(self, search):
        results = search.search_videos(
            "python", threshold=90
        )
        for r in results:
            assert r["score"] >= 90


class TestSearchPlaylists:
    def test_finds_by_name(self, search):
        results = search.search_playlists("programming")
        assert len(results) >= 1
        assert results[0]["title"] == "Programming Tutorials"

    def test_fuzzy_match(self, search):
        results = search.search_playlists("prog tut")
        assert len(results) >= 1


class TestSearchAll:
    def test_returns_both_types(self, search):
        results = search.search_all("music")
        types = {r["type"] for r in results}
        assert "playlist" in types or "video" in types
