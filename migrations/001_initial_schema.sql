CREATE TABLE playlists (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    privacy_status TEXT DEFAULT 'private',
    video_count INTEGER DEFAULT 0,
    source TEXT DEFAULT 'api',
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT (datetime('now')),
    updated_at TIMESTAMP DEFAULT (datetime('now'))
);

CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    channel_id TEXT DEFAULT '',
    channel_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    duration INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    thumbnail_url TEXT DEFAULT '',
    is_available BOOLEAN DEFAULT 1,
    watch_progress REAL DEFAULT 0.0,
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT (datetime('now'))
);

CREATE TABLE playlist_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id TEXT NOT NULL REFERENCES playlists(id),
    video_id TEXT NOT NULL REFERENCES videos(id),
    playlist_item_id TEXT DEFAULT '',
    position INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT (datetime('now')),
    UNIQUE(playlist_id, video_id)
);

CREATE TABLE watch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT DEFAULT '',
    title TEXT DEFAULT '',
    channel_name TEXT DEFAULT '',
    watched_at TIMESTAMP,
    source TEXT DEFAULT 'takeout'
);

CREATE TABLE liked_videos (
    video_id TEXT PRIMARY KEY,
    liked_at TIMESTAMP
);

CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL REFERENCES videos(id),
    playlist_id TEXT REFERENCES playlists(id),
    file_path TEXT DEFAULT '',
    quality TEXT DEFAULT '',
    downloaded_at TIMESTAMP DEFAULT (datetime('now')),
    file_size INTEGER DEFAULT 0
);

CREATE INDEX idx_videos_channel ON videos(channel_name);
CREATE INDEX idx_playlist_videos_playlist ON playlist_videos(playlist_id);
CREATE INDEX idx_playlist_videos_video ON playlist_videos(video_id);
CREATE INDEX idx_watch_history_video ON watch_history(video_id);
CREATE INDEX idx_watch_history_watched ON watch_history(watched_at);
