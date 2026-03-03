from __future__ import annotations


class VideoClient:
    def __init__(self, youtube):
        self.youtube = youtube

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """Get detailed info for up to 50 videos at a time."""
        videos = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            response = (
                self.youtube.videos()
                .list(
                    part="snippet,contentDetails,status",
                    id=",".join(chunk),
                )
                .execute()
            )
            videos.extend(response.get("items", []))
        return videos
