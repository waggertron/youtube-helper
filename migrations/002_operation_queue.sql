-- migrations/002_operation_queue.sql
CREATE TABLE operation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    params TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    progress REAL DEFAULT 0.0,
    message TEXT DEFAULT '',
    error TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX idx_queue_status ON operation_queue(status);
