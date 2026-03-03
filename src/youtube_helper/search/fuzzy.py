from __future__ import annotations

from thefuzz import fuzz, process

from youtube_helper.db.connection import get_connection


class FuzzySearch:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def search_videos(
        self, query: str, threshold: int = 60, limit: int = 20
    ) -> list[dict]:
        conn = get_connection(self.db_path)
        rows = conn.execute(
            "SELECT id, title, channel_name, "
            "watch_progress, duration FROM videos"
        ).fetchall()
        conn.close()
        videos = [dict(r) for r in rows]
        if not videos:
            return []
        choices = {
            v["id"]: f"{v['title']} {v['channel_name']}"
            for v in videos
        }
        matches = process.extract(
            query, choices, scorer=fuzz.WRatio, limit=limit
        )
        results = []
        for match_text, score, vid_id in matches:
            if score >= threshold:
                video = next(
                    v for v in videos if v["id"] == vid_id
                )
                video["score"] = score
                results.append(video)
        return results

    def search_playlists(
        self, query: str, threshold: int = 60, limit: int = 10
    ) -> list[dict]:
        conn = get_connection(self.db_path)
        rows = conn.execute(
            "SELECT id, title, video_count FROM playlists"
        ).fetchall()
        conn.close()
        playlists = [dict(r) for r in rows]
        if not playlists:
            return []
        choices = {p["id"]: p["title"] for p in playlists}
        matches = process.extract(
            query, choices, scorer=fuzz.WRatio, limit=limit
        )
        results = []
        for match_text, score, pl_id in matches:
            if score >= threshold:
                playlist = next(
                    p for p in playlists if p["id"] == pl_id
                )
                playlist["score"] = score
                results.append(playlist)
        return results

    def search_all(
        self, query: str, threshold: int = 60
    ) -> list[dict]:
        results = []
        for v in self.search_videos(query, threshold):
            v["type"] = "video"
            results.append(v)
        for p in self.search_playlists(query, threshold):
            p["type"] = "playlist"
            results.append(p)
        results.sort(
            key=lambda x: x.get("score", 0), reverse=True
        )
        return results
