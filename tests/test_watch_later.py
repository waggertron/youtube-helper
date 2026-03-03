from youtube_helper.browser.watch_later import (
    parse_duration_text,
    parse_progress_bar,
    parse_video_entry,
)


class TestParseDurationText:
    def test_minutes_seconds(self):
        assert parse_duration_text("10:30") == 630

    def test_hours_minutes_seconds(self):
        assert parse_duration_text("1:30:00") == 5400

    def test_seconds_only(self):
        assert parse_duration_text("45") == 45

    def test_empty_string(self):
        assert parse_duration_text("") == 0

    def test_whitespace(self):
        assert parse_duration_text("  10:30  ") == 630

    def test_invalid(self):
        assert parse_duration_text("abc") == 0


class TestParseProgressBar:
    def test_parses_percentage_from_width(self):
        assert parse_progress_bar("width: 75%") == 75.0

    def test_zero_for_no_progress(self):
        assert parse_progress_bar("") == 0.0

    def test_handles_decimal(self):
        assert parse_progress_bar("width: 33.5%") == 33.5

    def test_handles_no_space(self):
        assert parse_progress_bar("width:50%") == 50.0


class TestParseVideoEntry:
    def test_parses_valid_entry(self):
        entry = {
            "video_id": "abc123",
            "title": "Test Video",
            "channel": "Test Channel",
            "duration_text": "10:30",
            "progress_percent": 75.0,
            "thumbnail_url": "https://i.ytimg.com/vi/abc123/default.jpg",
        }
        result = parse_video_entry(entry)
        assert result["video_id"] == "abc123"
        assert result["title"] == "Test Video"
        assert result["duration_seconds"] == 630
        assert result["progress_percent"] == 75.0

    def test_parses_hours_duration(self):
        entry = {
            "video_id": "xyz",
            "title": "Long Video",
            "channel": "Ch",
            "duration_text": "1:30:00",
            "progress_percent": 0.0,
            "thumbnail_url": "",
        }
        result = parse_video_entry(entry)
        assert result["duration_seconds"] == 5400

    def test_handles_missing_duration(self):
        entry = {
            "video_id": "xyz",
            "title": "Live",
            "channel": "Ch",
            "duration_text": "",
            "progress_percent": 0.0,
            "thumbnail_url": "",
        }
        result = parse_video_entry(entry)
        assert result["duration_seconds"] == 0
