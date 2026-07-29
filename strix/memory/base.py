"""
strix/memory/base.py — Memory Interface
=========================================
Abstract base class for all memory backends.
Implementations: ConversationMemory (short-term), PersistentMemory (SQLite).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from strix.types import Message


class BaseMemory(ABC):
    """
    Abstract interface for memory storage backends.

    Memory stores conversation history, user preferences, and contextual data
    that persists across sessions or within a single conversation.

    Plugin contract:
        - Implement save(), get_recent(), search() for message storage
        - Implementations can be in-memory, SQLite, vector DB, etc.
    """

    @abstractmethod
    def save(
        self,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        intent: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Save a message to memory.

        Args:
            role: "user", "assistant", or "system"
            content: The message text
            session_id: Optional session identifier
            intent: Optional classified intent string
            metadata: Optional additional metadata
        """
        ...

    @abstractmethod
    def get_recent(self, limit: int = 10, session_id: Optional[str] = None) -> list[Message]:
        """
        Retrieve recent messages, optionally filtered by session.

        Args:
            limit: Maximum number of messages to return
            session_id: Optional session filter

        Returns:
            List of Message objects, newest last.
        """
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[Message]:
        """
        Search memory for relevant messages.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of Message objects ranked by relevance.
        """
        ...

    @abstractmethod
    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear messages, optionally for a specific session only."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name of this memory backend."""
        return self.__class__.__name__
