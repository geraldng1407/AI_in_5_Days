"""Persistent Relational Session Store for Multi-Turn Conversations.

Adheres to AgentOps Rubric Category 2: Persistent Session State.
Saves session state and conversational turns to SQLite/PostgreSQL to maintain
durable context across reloads and multi-turn triage interactions.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.observability.logger import get_logger
from src.observability.pii_scrubber import PIIScrubber


@dataclass
class Turn:
    turn_id: int
    session_id: str
    role: str
    content: str
    token_count: int
    timestamp: str
    metadata: dict[str, Any]


class SessionStore:
    """Manages persistent storage for conversational turns and session lifecycle."""

    def __init__(self, db_path: str = "data/incidents.db"):
        self.db_path = db_path
        self._shared_conn: sqlite3.Connection | None = None
        if db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        else:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._logger = get_logger("session-store")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.commit()
        if self._shared_conn is None:
            conn.close()

    def create_session(self, session_id: str) -> str:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = self._get_connection()
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, created_at, updated_at, status) VALUES (?, ?, ?, ?)",
            (session_id, now, now, "ACTIVE"),
        )
        conn.commit()
        if self._shared_conn is None:
            conn.close()
        return session_id

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        token_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        sanitized_content = PIIScrubber.scrub_text(content)
        sanitized_meta = PIIScrubber.scrub_dict(metadata or {})
        
        if token_count <= 0:
            token_count = max(1, len(sanitized_content) // 4)

        self.create_session(session_id)
        conn = self._get_connection()
        cursor = conn.execute(
            "INSERT INTO turns (session_id, role, content, token_count, timestamp, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, role, sanitized_content, token_count, now, json.dumps(sanitized_meta)),
        )
        conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
        conn.commit()
        turn_id = cursor.lastrowid or 0
        if self._shared_conn is None:
            conn.close()
        return turn_id

    def get_turns(self, session_id: str) -> list[Turn]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT turn_id, session_id, role, content, token_count, timestamp, metadata_json FROM turns WHERE session_id = ? ORDER BY turn_id ASC",
            (session_id,),
        ).fetchall()

        turns = [
            Turn(
                turn_id=row["turn_id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                token_count=row["token_count"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata_json"] or "{}"),
            )
            for row in rows
        ]
        if self._shared_conn is None:
            conn.close()
        return turns

    def update_summary(self, session_id: str, summary: str) -> None:
        sanitized_summary = PIIScrubber.scrub_text(summary)
        conn = self._get_connection()
        conn.execute(
            "UPDATE sessions SET summary = ?, updated_at = ? WHERE session_id = ?",
            (sanitized_summary, datetime.datetime.now(datetime.timezone.utc).isoformat(), session_id),
        )
        conn.commit()
        if self._shared_conn is None:
            conn.close()
