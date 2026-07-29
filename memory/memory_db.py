"""
memory/memory_db.py
-------------------
Handles all SQLite operations for JARVIS memory.
Stores: chat summaries, user preferences, task history.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis_memory.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn


def initialize_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("[Memory] Database initialized.")


# ── Chat History ─────────────────────────────────────────────

def save_message(role: str, content: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    # Also log to Obsidian Daily Notes
    try:
        from memory.obsidian_memory import get_obsidian_memory
        get_obsidian_memory().log_message(role, content)
    except Exception as e:
        print(f"[Memory] Obsidian log error: {e}")


def get_recent_messages(limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def clear_chat_history():
    conn = get_connection()
    conn.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()


# ── User Preferences ─────────────────────────────────────────

def set_preference(key: str, value):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
        (key, json.dumps(value), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_preference(key: str, default=None):
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM user_preferences WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return default


def get_all_preferences() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
    conn.close()
    return {r["key"]: json.loads(r["value"]) for r in rows}


# ── Task History ─────────────────────────────────────────────

def save_task(task: str, status: str, result: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO task_history (task, status, result, timestamp) VALUES (?, ?, ?, ?)",
        (task, status, result, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_recent_tasks(limit: int = 10) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT task, status, result, timestamp FROM task_history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
initialize_db()