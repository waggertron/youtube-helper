from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from youtube_helper.api.playlists import PlaylistClient


@pytest.fixture
def mock_youtube():
    return MagicMock()


@pytest.fixture
def client(mock_youtube):
    return PlaylistClient(mock_youtube)


class TestListPlaylists:
    def test_returns_playlists(self, client, mock_youtube):
        mock_youtube.playlists().list().execute.return_value = {
            "items": [
                {
                    "id": "PL123",
                    "snippet": {"title": "Test Playlist", "description": "desc"},
                    "status": {"privacyStatus": "private"},
                    "contentDetails": {"itemCount": 5},
                }
            ],
            "nextPageToken": None,
        }
        mock_youtube.playlists().list_next.return_value = None
        playlists = client.list_playlists()
        assert len(playlists) == 1
        assert playlists[0]["id"] == "PL123"


class TestListPlaylistItems:
    def test_returns_items(self, client, mock_youtube):
        mock_youtube.playlistItems().list().execute.return_value = {
            "items": [
                {
                    "id": "PLI123",
                    "snippet": {
                        "title": "Video 1",
                        "position": 0,
                        "resourceId": {"videoId": "VID1"},
                        "videoOwnerChannelTitle": "Channel 1",
                        "videoOwnerChannelId": "CH1",
                    },
                    "contentDetails": {"videoId": "VID1"},
                }
            ],
        }
        mock_youtube.playlistItems().list_next.return_value = None
        items = client.list_playlist_items("PL123")
        assert len(items) == 1
        assert items[0]["snippet"]["title"] == "Video 1"


class TestAddToPlaylist:
    def test_inserts_item(self, client, mock_youtube):
        mock_youtube.playlistItems().insert().execute.return_value = {
            "id": "PLI456",
        }
        result = client.add_to_playlist("PL123", "VID1")
        assert result["id"] == "PLI456"


class TestRemoveFromPlaylist:
    def test_deletes_item(self, client, mock_youtube):
        mock_youtube.playlistItems().delete().execute.return_value = ""
        client.remove_from_playlist("PLI123")
        mock_youtube.playlistItems().delete.assert_called()


class TestCreatePlaylist:
    def test_creates_private_playlist(self, client, mock_youtube):
        mock_youtube.playlists().insert().execute.return_value = {
            "id": "PL_NEW",
            "snippet": {"title": "New Playlist"},
        }
        result = client.create_playlist("New Playlist", privacy="private")
        assert result["id"] == "PL_NEW"
