"""Database layer for application settings and chat history persistence.

Uses a normalized SQLite database completely separate from the vectorstore/Chroma.
Provides clean, typed, thread-safe access to:
  - Key-value configuration settings (e.g. current vault directory, active session).
  - Normalized chat conversations (with model metadata, is_pinned flag) and messages (with timestamp/hora).
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
DEFAULT_VAULT_PATH = "/home/alerrsi/Documents/Obsidian"
DEFAULT_MODEL = "gemini-2.5-flash"

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
    model: str
    created_at: str
    updated_at: str
    is_pinned: bool = False


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
            # Normalizada con id, nombre/title, modelo usado, is_pinned, created_at, updated_at
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT 'gemini-2.5-flash',
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            # Migrations: Ensure model and is_pinned columns exist
            cursor = conn.execute("PRAGMA table_info(chat_sessions);")
            columns = [col["name"] for col in cursor.fetchall()]
            if "model" not in columns:
                conn.execute(
                    f"ALTER TABLE chat_sessions ADD COLUMN model TEXT NOT NULL DEFAULT '{DEFAULT_MODEL}';"
                )
            if "is_pinned" not in columns:
                conn.execute(
                    "ALTER TABLE chat_sessions ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0;"
                )

            # 3. Chat messages table: normalizada con id, session_id, sender, content, thought, created_at (hora)
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
                "CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(is_pinned DESC, updated_at DESC);"
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

    def get_most_recent_session(self) -> ChatSession | None:
        """Returns the most recent persisted session with at least one message, or None."""
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT s.id, s.title, s.model, s.is_pinned, s.created_at, s.updated_at
                FROM chat_sessions s
                INNER JOIN chat_messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.is_pinned DESC, s.updated_at DESC
                LIMIT 1;
                """
            )
            row = cursor.fetchone()
            if row is not None:
                return ChatSession(
                    id=row["id"],
                    title=row["title"],
                    model=row["model"],
                    is_pinned=bool(row["is_pinned"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        return None

    def get_or_create_default_session(self) -> ChatSession:
        """Returns the most recent persisted session or creates an initial one."""
        session = self.get_most_recent_session()
        if session is not None:
            return session
        return self.create_session("Conversación Inicial")

    def create_session(
        self,
        title: str = "Nueva Conversación",
        model: str = DEFAULT_MODEL,
        session_id: str | None = None,
        is_pinned: bool = False,
    ) -> ChatSession:
        """Explicitly saves a new chat session to SQLite with id, title, and model."""
        sess_id = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with _LOCK, self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, title, model, is_pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    model = excluded.model,
                    is_pinned = excluded.is_pinned,
                    updated_at = excluded.updated_at;
                """,
                (sess_id, title, model, 1 if is_pinned else 0, now, now),
            )
            conn.commit()
        return ChatSession(
            id=sess_id,
            title=title,
            model=model,
            is_pinned=is_pinned,
            created_at=now,
            updated_at=now,
        )

    def session_exists(self, session_id: str) -> bool:
        """Checks if a session is currently stored in SQLite."""
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM chat_sessions WHERE id = ?;", (session_id,))
            return cursor.fetchone() is not None

    def list_sessions(self, require_messages: bool = True) -> list[ChatSession]:
        """Lists chat sessions ordered with pinned chats first, then newest updated.

        By default, excludes ghost sessions without any messages.
        """
        query = """
            SELECT s.id, s.title, s.model, s.is_pinned, s.created_at, s.updated_at
            FROM chat_sessions s
        """
        if require_messages:
            query += """
            INNER JOIN chat_messages m ON s.id = m.session_id
            GROUP BY s.id
            """
        query += " ORDER BY s.is_pinned DESC, s.updated_at DESC;"

        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute(query)
            return [
                ChatSession(
                    id=row["id"],
                    title=row["title"],
                    model=row["model"],
                    is_pinned=bool(row["is_pinned"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in cursor.fetchall()
            ]

    def count_pinned_sessions(self) -> int:
        """Returns the number of currently pinned sessions."""
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chat_sessions WHERE is_pinned = 1;")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def toggle_pin_session(self, session_id: str) -> tuple[bool, str]:
        """Toggles the pinned status of a session. Enforces a maximum of 3 pinned chats.

        Returns (success, message).
        """
        with _LOCK, self._get_connection() as conn:
            cursor = conn.execute("SELECT is_pinned FROM chat_sessions WHERE id = ?;", (session_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Conversación no encontrada"

            current_status = bool(row["is_pinned"])
            if not current_status:
                pinned_count = self.count_pinned_sessions()
                if pinned_count >= 3:
                    return False, "Máximo 3 conversaciones fijadas permitidas."
                new_status = 1
                msg = "Conversación fijada"
            else:
                new_status = 0
                msg = "Conversación desfijada"

            conn.execute("UPDATE chat_sessions SET is_pinned = ? WHERE id = ?;", (new_status, session_id))
            conn.commit()
            return True, msg

    def add_message(
        self,
        session_id: str,
        sender: str,
        content: str,
        thought: str | None = None,
        created_at: str | None = None,
    ) -> MessageRecord:
        msg_id = str(uuid.uuid4())
        now = created_at or datetime.now(timezone.utc).isoformat()
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
