from __future__ import annotations

from youtube_helper.db.connection import get_connection


class WatchLaterManager:
    WATCH_LATER_ID = "WL"

    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_scraped_videos(self, videos: list[dict]) -> int:
        """Save scraped Watch Later videos into the database."""
        conn = get_connection(self.db_path)
        conn.execute(
            """INSERT INTO playlists
               (id, title, privacy_status, source)
               VALUES (?, 'Watch Later', 'private', 'browser')
               ON CONFLICT(id) DO UPDATE SET
               last_synced=datetime('now')""",
            (self.WATCH_LATER_ID,),
        )
        saved = 0
        for i, v in enumerate(videos):
            conn.execute(
                """INSERT INTO videos
                   (id, title, channel_name, duration,
                    watch_progress, thumbnail_url, last_synced)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(id) DO UPDATE SET
                       title=excluded.title,
                       channel_name=excluded.channel_name,
                       duration=excluded.duration,
                       watch_progress=excluded.watch_progress,
                       thumbnail_url=excluded.thumbnail_url,
                       last_synced=excluded.last_synced""",
                (
                    v["video_id"],
                    v["title"],
                    v["channel"],
                    v["duration_seconds"],
                    v["progress_percent"],
                    v.get("thumbnail_url", ""),
                ),
            )
            conn.execute(
                """INSERT INTO playlist_videos
                   (playlist_id, video_id,
                    playlist_item_id, position)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(playlist_id, video_id)
                   DO UPDATE SET position=excluded.position""",
                (self.WATCH_LATER_ID, v["video_id"], "", i),
            )
            saved += 1
        conn.commit()
        conn.close()
        return saved

    def get_watched_videos(
        self, threshold: float = 50.0
    ) -> list[dict]:
        """Get videos watched above the given threshold."""
        conn = get_connection(self.db_path)
        rows = conn.execute(
            """SELECT v.* FROM videos v
               JOIN playlist_videos pv ON v.id = pv.video_id
               WHERE pv.playlist_id = ?
               AND v.watch_progress >= ?
               ORDER BY v.watch_progress DESC""",
            (self.WATCH_LATER_ID, threshold),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_unwatched_videos(
        self, threshold: float = 50.0
    ) -> list[dict]:
        """Get videos watched below the given threshold."""
        conn = get_connection(self.db_path)
        rows = conn.execute(
            """SELECT v.* FROM videos v
               JOIN playlist_videos pv ON v.id = pv.video_id
               WHERE pv.playlist_id = ?
               AND v.watch_progress < ?
               ORDER BY pv.position""",
            (self.WATCH_LATER_ID, threshold),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def export_playlist_data(
        self, playlist_id: str
    ) -> list[dict]:
        """Export all video data for a playlist."""
        conn = get_connection(self.db_path)
        rows = conn.execute(
            """SELECT v.*, pv.position, pv.playlist_item_id
               FROM videos v
               JOIN playlist_videos pv ON v.id = pv.video_id
               WHERE pv.playlist_id = ?
               ORDER BY pv.position""",
            (playlist_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def remove_videos_from_db(
        self, playlist_id: str, video_ids: list[str]
    ) -> int:
        """Remove videos from a playlist in the database."""
        conn = get_connection(self.db_path)
        removed = 0
        for vid in video_ids:
            conn.execute(
                "DELETE FROM playlist_videos "
                "WHERE playlist_id = ? AND video_id = ?",
                (playlist_id, vid),
            )
            removed += 1
        conn.commit()
        conn.close()
        return removed
