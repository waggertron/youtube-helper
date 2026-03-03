from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from youtube_helper.api.videos import VideoClient


@pytest.fixture
def mock_youtube():
    return MagicMock()


@pytest.fixture
def client(mock_youtube):
    return VideoClient(mock_youtube)


class TestGetVideoDetails:
    def test_returns_video_details(self, client, mock_youtube):
        mock_youtube.videos().list().execute.return_value = {
            "items": [{"id": "VID1", "snippet": {"title": "Test"}}],
        }
        result = client.get_video_details(["VID1"])
        assert len(result) == 1
        assert result[0]["id"] == "VID1"

    def test_handles_empty_list(self, client):
        result = client.get_video_details([])
        assert result == []
