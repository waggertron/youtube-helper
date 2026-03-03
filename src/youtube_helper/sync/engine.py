from __future__ import annotations

from datetime import UTC, datetime

from youtube_helper.api.playlists import PlaylistClient
from youtube_helper.db.connection import get_connection


class SyncEngine:
    def __init__(self, db_path: str, playlist_client: PlaylistClient):
        self.db_path = db_path
        self.client = playlist_client

    def sync_all(self, verbose: bool = False) -> dict:
        stats = {"playlists": 0, "videos": 0, "relationships": 0}
        conn = get_connection(self.db_path)
        now = datetime.now(UTC).isoformat()

        playlists = self.client.list_playlists()
        stats["playlists"] = len(playlists)

        for pl in playlists:
            conn.execute(
                """INSERT INTO playlists
                   (id, title, description, privacy_status,
                    video_count, source, last_synced)
                   VALUES (?, ?, ?, ?, ?, 'api', ?)
                   ON CONFLICT(id) DO UPDATE SET
                       title=excluded.title,
                       description=excluded.description,
                       privacy_status=excluded.privacy_status,
                       video_count=excluded.video_count,
                       last_synced=excluded.last_synced,
                       updated_at=datetime('now')""",
                (
                    pl["id"],
                    pl["snippet"]["title"],
                    pl["snippet"].get("description", ""),
                    pl["status"]["privacyStatus"],
                    pl["contentDetails"]["itemCount"],
                    now,
                ),
            )
            conn.commit()

            items = self.client.list_playlist_items(pl["id"])

            for item in items:
                video_id = item["snippet"]["resourceId"]["videoId"]
                title = item["snippet"].get("title", "")
                channel_name = item["snippet"].get(
                    "videoOwnerChannelTitle", ""
                )
                channel_id = item["snippet"].get(
                    "videoOwnerChannelId", ""
                )
                published = item["contentDetails"].get(
                    "videoPublishedAt", ""
                )
                playlist_item_id = item["id"]
                position = item["snippet"].get("position", 0)

                conn.execute(
                    """INSERT INTO videos
                       (id, title, channel_id, channel_name,
                        published_at, last_synced)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           title=excluded.title,
                           channel_id=excluded.channel_id,
                           channel_name=excluded.channel_name,
                           published_at=excluded.published_at,
                           last_synced=excluded.last_synced""",
                    (
                        video_id, title, channel_id,
                        channel_name, published, now,
                    ),
                )

                conn.execute(
                    """INSERT INTO playlist_videos
                       (playlist_id, video_id,
                        playlist_item_id, position)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(playlist_id, video_id)
                       DO UPDATE SET
                           playlist_item_id=excluded.playlist_item_id,
                           position=excluded.position""",
                    (pl["id"], video_id, playlist_item_id, position),
                )
                conn.commit()

                stats["videos"] += 1
                stats["relationships"] += 1

        conn.close()
        return stats
