# src/youtube_helper/web/queue.py
from __future__ import annotations

import json

from youtube_helper.db.connection import get_connection


class QueueManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def submit(self, op_type: str, params: dict) -> int:
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            "INSERT INTO operation_queue (type, params) VALUES (?, ?)",
            (op_type, json.dumps(params)),
        )
        conn.commit()
        op_id = cursor.lastrowid
        conn.close()
        return op_id

    def list_operations(self) -> list[dict]:
        conn = get_connection(self.db_path)
        rows = conn.execute(
            "SELECT * FROM operation_queue ORDER BY id"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_operation(self, op_id: int) -> dict | None:
        conn = get_connection(self.db_path)
        row = conn.execute(
            "SELECT * FROM operation_queue WHERE id = ?", (op_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_operation(
        self,
        op_id: int,
        status: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> None:
        conn = get_connection(self.db_path)
        updates = []
        values = []
        if status is not None:
            updates.append("status = ?")
            values.append(status)
            if status == "active":
                updates.append("started_at = datetime('now')")
            elif status in ("completed", "failed"):
                updates.append("completed_at = datetime('now')")
        if progress is not None:
            updates.append("progress = ?")
            values.append(progress)
        if message is not None:
            updates.append("message = ?")
            values.append(message)
        if error is not None:
            updates.append("error = ?")
            values.append(error)
        values.append(op_id)
        conn.execute(
            f"UPDATE operation_queue SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        conn.commit()
        conn.close()

    def cancel_operation(self, op_id: int) -> bool:
        op = self.get_operation(op_id)
        if not op or op["status"] != "pending":
            return False
        self.update_operation(op_id, status="cancelled")
        return True

    def next_pending(self) -> dict | None:
        conn = get_connection(self.db_path)
        row = conn.execute(
            "SELECT * FROM operation_queue WHERE status = 'pending' ORDER BY id LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None
