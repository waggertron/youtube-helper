from __future__ import annotations


class PlaylistClient:
    def __init__(self, youtube):
        self.youtube = youtube

    def list_playlists(self) -> list[dict]:
        playlists = []
        request = self.youtube.playlists().list(
            part="snippet,status,contentDetails",
            mine=True,
            maxResults=50,
        )
        while request:
            response = request.execute()
            playlists.extend(response.get("items", []))
            request = self.youtube.playlists().list_next(request, response)
        return playlists

    def list_playlist_items(self, playlist_id: str) -> list[dict]:
        items = []
        request = self.youtube.playlistItems().list(
            part="snippet,contentDetails,status",
            playlistId=playlist_id,
            maxResults=50,
        )
        while request:
            response = request.execute()
            items.extend(response.get("items", []))
            request = self.youtube.playlistItems().list_next(
                request, response
            )
        return items

    def add_to_playlist(
        self,
        playlist_id: str,
        video_id: str,
        position: int | None = None,
    ) -> dict:
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        }
        if position is not None:
            body["snippet"]["position"] = position
        return (
            self.youtube.playlistItems()
            .insert(
                part="snippet",
                body=body,
            )
            .execute()
        )

    def remove_from_playlist(self, playlist_item_id: str) -> None:
        self.youtube.playlistItems().delete(id=playlist_item_id).execute()

    def create_playlist(
        self,
        title: str,
        description: str = "",
        privacy: str = "private",
    ) -> dict:
        return (
            self.youtube.playlists()
            .insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                    },
                    "status": {
                        "privacyStatus": privacy,
                    },
                },
            )
            .execute()
        )
