# tests/test_browser_purge.py
import pytest
from unittest.mock import AsyncMock, patch

from youtube_helper.browser.watch_later import purge_videos_from_watch_later


@pytest.mark.asyncio
async def test_purge_calls_remove_for_each_video():
    video_ids = ["abc123", "def456"]

    with patch("playwright.async_api.async_playwright") as mock_pw:
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]

        mock_browser = AsyncMock()
        mock_browser.chromium.launch_persistent_context.return_value = mock_context

        mock_pw_instance = AsyncMock()
        mock_pw_instance.__aenter__.return_value = mock_browser
        mock_pw.return_value = mock_pw_instance

        with patch("youtube_helper.browser.watch_later._remove_video_from_page") as mock_remove:
            mock_remove.return_value = True

            updates = []

            def track_update(**kwargs):
                updates.append(kwargs)

            result = await purge_videos_from_watch_later(
                video_ids=video_ids, update=track_update, headless=True
            )
            assert result["removed"] == 2
            assert mock_remove.call_count == 2
            assert len(updates) == 2


@pytest.mark.asyncio
async def test_purge_handles_remove_failure():
    video_ids = ["abc123", "def456"]

    with patch("playwright.async_api.async_playwright") as mock_pw:
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.pages = [mock_page]

        mock_browser = AsyncMock()
        mock_browser.chromium.launch_persistent_context.return_value = mock_context

        mock_pw_instance = AsyncMock()
        mock_pw_instance.__aenter__.return_value = mock_browser
        mock_pw.return_value = mock_pw_instance

        with patch("youtube_helper.browser.watch_later._remove_video_from_page") as mock_remove:
            # First succeeds, second fails
            mock_remove.side_effect = [True, False]

            updates = []

            def track_update(**kwargs):
                updates.append(kwargs)

            result = await purge_videos_from_watch_later(
                video_ids=video_ids, update=track_update, headless=True
            )
            assert result["removed"] == 1
            assert result["skipped"] == 1
            assert result["failed"] == 0
