"""
Long-term SQLite Storage for Strix v5.0
"""
from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from strix.types import Message
from strix.memory.base import BaseMemory
from strix.config import StrixConfig

class PersistentMemory(BaseMemory):
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            config = StrixConfig.load()
            db_path = config.ROOT_DIR / 'memory' / 'strix_memory.db'
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.initialize()

    def initialize(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    intent TEXT,
                    metadata TEXT
                )
            """)

    def save(
        self,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        intent: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        timestamp = datetime.now().isoformat()
        metadata_str = json.dumps(metadata) if metadata else "{}"
        
        with self.conn:
            self.conn.execute("""
                INSERT INTO messages (role, content, timestamp, session_id, intent, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (role, content, timestamp, session_id, intent, metadata_str))
        
        print(f"[STRIX PersistentMemory] Saved {role} message ({len(content)} chars)")

    def get_recent(self, limit: int = 10, session_id: Optional[str] = None) -> List[Message]:
        query = "SELECT role, content, timestamp, session_id, intent, metadata FROM messages"
        params = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        messages = []
        for row in reversed(rows):
            role, content, timestamp, sess_id, intent, metadata_str = row
            msg = Message(role=role, content=content, session_id=sess_id)
            if intent:
                msg.intent = intent
            if metadata_str:
                msg.metadata = json.loads(metadata_str)
            msg.timestamp = timestamp
            messages.append(msg)
            
        return messages

    def search(self, query: str, limit: int = 5, session_id: Optional[str] = None) -> List[Message]:
        sql_query = "SELECT role, content, timestamp, session_id, intent, metadata FROM messages WHERE content LIKE ?"
        params = [f"%{query}%"]
        if session_id:
            sql_query += " AND session_id = ?"
            params.append(session_id)
        sql_query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(sql_query, params)
        rows = cursor.fetchall()

        messages = []
        for row in reversed(rows):
            role, content, timestamp, sess_id, intent, metadata_str = row
            msg = Message(role=role, content=content, session_id=sess_id)
            if intent:
                msg.intent = intent
            if metadata_str:
                msg.metadata = json.loads(metadata_str)
            msg.timestamp = timestamp
            messages.append(msg)
            
        return messages

    def clear(self, session_id: Optional[str] = None) -> None:
        with self.conn:
            if session_id:
                self.conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            else:
                self.conn.execute("DELETE FROM messages")

    def get_stats(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM messages WHERE session_id IS NOT NULL")
        unique_sessions = cursor.fetchone()[0]
        
        return {
            "total_messages": total_messages,
            "unique_sessions": unique_sessions
        }
