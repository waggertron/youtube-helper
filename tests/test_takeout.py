import json
import pytest
from youtube_helper.takeout import parse_takeout_watch_later


def test_parse_takeout_json():
    """Takeout exports playlist as JSON with video URLs."""
    takeout_data = json.dumps([
        {
            "contentDetails": {
                "videoId": "dQw4w9WgXcQ",
                "videoPublishedAt": "2009-10-25T06:57:33.000Z"
            },
            "snippet": {
                "title": "Rick Astley - Never Gonna Give You Up",
                "position": 0,
                "resourceId": {"videoId": "dQw4w9WgXcQ"}
            }
        },
        {
            "contentDetails": {
                "videoId": "abc123def45",
                "videoPublishedAt": "2020-01-01T00:00:00.000Z"
            },
            "snippet": {
                "title": "Another Video",
                "position": 1,
                "resourceId": {"videoId": "abc123def45"}
            }
        }
    ])
    result = parse_takeout_watch_later(takeout_data.encode())
    assert len(result) == 2
    assert result[0]["video_id"] == "dQw4w9WgXcQ"
    assert result[0]["title"] == "Rick Astley - Never Gonna Give You Up"
    assert result[1]["video_id"] == "abc123def45"


def test_parse_takeout_csv():
    """Takeout sometimes exports as CSV."""
    csv_data = b"Video Id,Time Added\ndQw4w9WgXcQ,2024-01-15 10:30:00 UTC\nabc123def45,2024-02-20 15:00:00 UTC\n"
    result = parse_takeout_watch_later(csv_data)
    assert len(result) == 2
    assert result[0]["video_id"] == "dQw4w9WgXcQ"
    assert result[1]["video_id"] == "abc123def45"


def test_parse_takeout_extracts_ids_from_urls():
    """Some Takeout formats include full URLs."""
    takeout_data = json.dumps([
        {
            "titleUrl": "https://www.youtube.com/watch?v\\u003ddQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up"
        }
    ])
    result = parse_takeout_watch_later(takeout_data.encode())
    assert len(result) == 1
    assert result[0]["video_id"] == "dQw4w9WgXcQ"


def test_parse_empty_file():
    result = parse_takeout_watch_later(b"[]")
    assert result == []


def test_parse_invalid_data():
    with pytest.raises(ValueError, match="Could not parse"):
        parse_takeout_watch_later(b"not valid data at all")
