"""
User Preferences for Strix v5.0
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

class PreferencesStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.initialize()

    def initialize(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def set(self, key: str, value: str) -> None:
        updated_at = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, updated_at))
        print(f"[STRIX Preferences] Set {key} = {value}")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return default

    def get_all(self) -> Dict[str, str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM preferences")
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    def delete(self, key: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM preferences WHERE key = ?", (key,))

    def to_context_string(self) -> str:
        prefs = self.get_all()
        return "\n".join(f"{key}: {value}" for key, value in prefs.items())
