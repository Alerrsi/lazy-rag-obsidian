"""Database layer for application settings and chat history persistence.

Uses a normalized SQLite database completely separate from the vectorstore/Chroma.
Provides clean, typed, thread-safe access to:
  - Key-value configuration settings (e.g. current vault directory, active session).
  - Normalized chat conversations and messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any
import uuid

# Base path for application SQLite storage
DB_DIR = Path(__file__).resolve().parent
DB_FILE = DB_DIR / "app_data.sqlite"
DEFAULT_VAULT_PATH = "/home/alerrsi/Documents"

_LOCK = threading.RLock()


@dataclass(frozen=True)
class MessageRecord:
    id: str
    session_id: str
    sender: str
    content: str
    created_at: str
    thought: str | None = None


@dataclass(frozen=True)
class ChatSession:
    id: str
    title: str
    created_at: str
    updated_at: str


class AppDatabase:
    """Encapsulates SQLite connection management, schema migrations, and queries."""

    _instance: AppDatabase | None = None

    def __init__(self, db_path: Path | str = DB_FILE) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Path | str = DB_FILE) -> AppDatabase:
        with _LOCK:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        """Initializes tables for settings and normalized chat conversations."""
        with _LOCK, self._get_connection() as conn:
            # 1. Settings table: key-value storage for app configurations
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # 2. Chat sessions table (1:N relationship with messages)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # 3. Chat messages table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL, -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    thought TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );
                """
            )

            # Indexes for high performance queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id, created_at);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at DESC);"
            )

            # Ensure default settings are populated
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES ('vault_path', ?, ?);
                """,
                (DEFAULT_VAULT_PATH, now),
            )
            conn.commit()

    # --- Settings API --------------------------------------------------------

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?;", (key,))
            row = cursor.fetchone()
            if row is not None:
                return str(row["value"])
            return default

    def set_setting(self, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with _LOCK, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at;
                """,
                (key, str(value), now),
            )
            conn.commit()

    def get_vault_path(self) -> str:
        """Retrieves the currently configured vault directory from SQLite."""
        val = self.get_setting("vault_path", DEFAULT_VAULT_PATH)
        return val or DEFAULT_VAULT_PATH

    def set_vault_path(self, path: str) -> None:
        """Saves the current vault directory to SQLite."""
        abs_path = os.path.abspath(os.path.expanduser(path))
        self.set_setting("vault_path", abs_path)

    # --- Chat Sessions & Messages API ---------------------------------------

    def get_or_create_default_session(self) -> ChatSession:
        """Returns the most recent session or creates a new one."""
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT 1;"
            )
            row = cursor.fetchone()
            if row is not None:
                return ChatSession(
                    id=row["id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        return self.create_session("Conversación Inicial")

    def create_session(self, title: str = "Nueva Conversación") -> ChatSession:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with _LOCK, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?);
                """,
                (session_id, title, now, now),
            )
            conn.commit()
        return ChatSession(id=session_id, title=title, created_at=now, updated_at=now)

    def list_sessions(self) -> list[ChatSession]:
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC;"
            )
            return [
                ChatSession(
                    id=row["id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in cursor.fetchall()
            ]

    def add_message(
        self,
        session_id: str,
        sender: str,
        content: str,
        thought: str | None = None,
    ) -> MessageRecord:
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with _LOCK, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, sender, content, thought, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (msg_id, session_id, sender, content, thought, now),
            )
            # Update session's updated_at timestamp
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?;",
                (now, session_id),
            )
            conn.commit()

        return MessageRecord(
            id=msg_id,
            session_id=session_id,
            sender=sender,
            content=content,
            thought=thought,
            created_at=now,
        )

    def get_messages(self, session_id: str) -> list[MessageRecord]:
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, session_id, sender, content, thought, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC;
                """,
                (session_id,),
            )
            return [
                MessageRecord(
                    id=row["id"],
                    session_id=row["session_id"],
                    sender=row["sender"],
                    content=row["content"],
                    thought=row["thought"],
                    created_at=row["created_at"],
                )
                for row in cursor.fetchall()
            ]

    def delete_session(self, session_id: str) -> None:
        with _LOCK, self._get_connection() as conn:
            conn.execute("DELETE FROM chat_sessions WHERE id = ?;", (session_id,))
            conn.commit()
