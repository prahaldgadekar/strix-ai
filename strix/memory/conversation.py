"""
Short-term Conversation Buffer for Strix v5.0
"""
from __future__ import annotations

import threading
from typing import List, Optional

from strix.types import Message
from strix.memory.base import BaseMemory

class ConversationMemory(BaseMemory):
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._messages: List[Message] = []
        self._lock = threading.Lock()

    def save(
        self,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        intent: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        from datetime import datetime
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            session_id=session_id,
            metadata=metadata or {},
        )
        with self._lock:
            self._messages.append(message)
            if len(self._messages) > self.max_messages:
                self._messages.pop(0)
            print(f"[STRIX ConversationMemory] Saved {role} message ({len(content)} chars)")

    def get_recent(self, limit: int = 10, session_id: Optional[str] = None) -> List[Message]:
        with self._lock:
            msgs = self._messages
            if session_id:
                msgs = [m for m in msgs if m.session_id == session_id]
            return msgs[-limit:] if limit > 0 else msgs

    def search(self, query: str, limit: int = 5, session_id: Optional[str] = None) -> List[Message]:
        with self._lock:
            msgs = self._messages
            if session_id:
                msgs = [m for m in msgs if m.session_id == session_id]
            results = [m for m in msgs if query.lower() in m.content.lower()]
            return results[-limit:] if limit > 0 else results

    def clear(self, session_id: Optional[str] = None) -> None:
        with self._lock:
            if session_id:
                self._messages = [m for m in self._messages if m.session_id != session_id]
            else:
                self._messages = []

    def get_context_string(self, limit: int = 10, session_id: Optional[str] = None) -> str:
        msgs = self.get_recent(limit=limit, session_id=session_id)
        return "\n".join(f"{m.role}: {m.content}" for m in msgs)
