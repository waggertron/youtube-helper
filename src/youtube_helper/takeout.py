"""Parse Google Takeout Watch Later export files."""

import csv
import io
import json
import re


def parse_takeout_watch_later(data: bytes) -> list[dict]:
    """Parse a Takeout Watch Later export. Accepts JSON or CSV bytes.

    Returns list of dicts with at minimum: video_id, title (if available).
    """
    text = data.decode("utf-8").strip()

    # Try JSON first
    try:
        entries = json.loads(text)
        if isinstance(entries, list):
            return _parse_json_entries(entries)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try CSV
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if rows and ("Video Id" in rows[0] or "videoId" in rows[0]):
            return _parse_csv_rows(rows)
    except csv.Error:
        pass

    raise ValueError("Could not parse Takeout file as JSON or CSV")


def _parse_json_entries(entries: list[dict]) -> list[dict]:
    results = []
    for entry in entries:
        video_id = None
        title = entry.get("title", "")

        # Format 1: contentDetails.videoId or snippet.resourceId.videoId
        cd = entry.get("contentDetails", {})
        if "videoId" in cd:
            video_id = cd["videoId"]
        snippet = entry.get("snippet", {})
        rid = snippet.get("resourceId", {})
        if not video_id and "videoId" in rid:
            video_id = rid["videoId"]
        if not title and "title" in snippet:
            title = snippet["title"]

        # Format 2: titleUrl with encoded URL
        if not video_id and "titleUrl" in entry:
            url = entry["titleUrl"].replace("\\u003d", "=")
            match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
            if match:
                video_id = match.group(1)

        if video_id:
            results.append({"video_id": video_id, "title": title})
    return results


def _parse_csv_rows(rows: list[dict]) -> list[dict]:
    results = []
    for row in rows:
        video_id = row.get("Video Id") or row.get("videoId", "")
        video_id = video_id.strip()
        if video_id:
            results.append({"video_id": video_id, "title": row.get("Title", "")})
    return results
