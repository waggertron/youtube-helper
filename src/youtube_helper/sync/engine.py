from __future__ import annotations

import re
from datetime import UTC, datetime

from youtube_helper.api.playlists import PlaylistClient
from youtube_helper.db.connection import get_connection


def _parse_duration(iso_duration: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to total seconds."""
    match = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or ""
    )
    if not match:
        return 0
    h, m, s = (int(g) if g else 0 for g in match.groups())
    return h * 3600 + m * 60 + s


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

            # Batch-fetch video details (duration, thumbnails)
            video_ids = [
                item["snippet"]["resourceId"]["videoId"]
                for item in items
            ]
            video_details = self.client.get_video_details(video_ids)

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

                # Get duration and thumbnail from video details
                detail = video_details.get(video_id, {})
                duration = _parse_duration(
                    detail.get("contentDetails", {}).get("duration", "")
                )
                thumbnails = detail.get("snippet", {}).get("thumbnails", {})
                thumbnail_url = (
                    thumbnails.get("medium", {}).get("url", "")
                    or thumbnails.get("default", {}).get("url", "")
                )

                conn.execute(
                    """INSERT INTO videos
                       (id, title, channel_id, channel_name,
                        duration, thumbnail_url,
                        published_at, last_synced)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           title=excluded.title,
                           channel_id=excluded.channel_id,
                           channel_name=excluded.channel_name,
                           duration=excluded.duration,
                           thumbnail_url=excluded.thumbnail_url,
                           published_at=excluded.published_at,
                           last_synced=excluded.last_synced""",
                    (
                        video_id, title, channel_id,
                        channel_name, duration, thumbnail_url,
                        published, now,
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
                           position=excluded.position,
                           removed_at=NULL""",
                    (pl["id"], video_id, playlist_item_id, position),
                )
                conn.commit()

                stats["videos"] += 1
                stats["relationships"] += 1

        conn.close()
        return stats

    def sync_liked_videos(self) -> int:
        """Sync liked videos from YouTube. Returns count of liked videos synced."""
        youtube = self.client.youtube
        liked_ids: list[str] = []
        page_token = None

        while True:
            resp = youtube.videos().list(
                part="id,snippet,contentDetails",
                myRating="like",
                maxResults=50,
                pageToken=page_token,
            ).execute()

            conn = get_connection(self.db_path)
            for item in resp.get("items", []):
                vid_id = item["id"]
                liked_ids.append(vid_id)

                snippet = item.get("snippet", {})
                duration = _parse_duration(
                    item.get("contentDetails", {}).get("duration", "")
                )
                thumbnails = snippet.get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("medium", {}).get("url", "")
                    or thumbnails.get("default", {}).get("url", "")
                )

                conn.execute(
                    """INSERT INTO videos
                       (id, title, channel_id, channel_name,
                        duration, published_at, thumbnail_url,
                        last_synced)
                       VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                       ON CONFLICT(id) DO UPDATE SET
                           title=excluded.title,
                           channel_id=excluded.channel_id,
                           channel_name=excluded.channel_name,
                           duration=excluded.duration,
                           published_at=excluded.published_at,
                           thumbnail_url=excluded.thumbnail_url,
                           last_synced=datetime('now')""",
                    (
                        vid_id,
                        snippet.get("title", ""),
                        snippet.get("channelId", ""),
                        snippet.get("channelTitle", ""),
                        duration,
                        snippet.get("publishedAt", ""),
                        thumb_url,
                    ),
                )

                conn.execute(
                    """INSERT INTO liked_videos (video_id, liked_at)
                       VALUES (?, datetime('now'))
                       ON CONFLICT(video_id) DO UPDATE SET
                           liked_at=COALESCE(liked_videos.liked_at,
                                             datetime('now')),
                           removed_at=NULL""",
                    (vid_id,),
                )

            conn.commit()
            conn.close()

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return len(liked_ids)
