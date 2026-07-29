"""
memory/obsidian_memory.py
--------------------------
Obsidian Memory Integration for STRIX.
Manages daily notes, user profiles, topic wikilinks, and context retrieval.
"""

import os
import re
import glob
from datetime import datetime

class ObsidianMemoryManager:
    """
    Manages STRIX long-term memory and daily conversation logs in an Obsidian Vault.
    """

    def __init__(self, vault_path: str = None):
        if not vault_path:
            vault_path = os.getenv(
                "OBSIDIAN_VAULT_PATH",
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "strix core")
            )
        self.vault_path = os.path.abspath(vault_path)
        self.daily_notes_dir = os.path.join(self.vault_path, "Daily Notes")
        self._ensure_vault_structure()

    def _ensure_vault_structure(self):
        """Ensure vault directory and subfolders exist."""
        os.makedirs(self.vault_path, exist_ok=True)
        os.makedirs(self.daily_notes_dir, exist_ok=True)

    def _get_today_note_path(self) -> str:
        """Get absolute path to today's daily note (YYYY-MM-DD.md)."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.daily_notes_dir, f"{date_str}.md")

    def _extract_wikilinks(self, text: str) -> list:
        """Extract or generate wikilinks based on keywords in text."""
        links = []
        text_lower = text.lower()
        keywords = {
            "python": "[[Python]]",
            "java": "[[Java]]",
            "javascript": "[[JavaScript]]",
            "html": "[[HTML]]",
            "css": "[[CSS]]",
            "c++": "[[C++]]",
            "code": "[[Coding]]",
            "strix": "[[Strix]]",
            "spotify": "[[Spotify]]",
            "weather": "[[Weather]]",
            "news": "[[News]]",
            "git": "[[Git]]",
            "ollama": "[[Ollama]]",
        }
        for kw, link in keywords.items():
            if kw in text_lower and link not in links:
                links.append(link)
        return links

    def log_message(self, role: str, content: str):
        """Append a user or assistant message to today's daily note in Obsidian."""
        note_path = self._get_today_note_path()
        time_str = datetime.now().strftime("%H:%M:%S")
        wikilinks = self._extract_wikilinks(content)
        link_str = (" Tags: " + " ".join(wikilinks)) if wikilinks else ""

        is_new_file = not os.path.exists(note_path)

        with open(note_path, "a", encoding="utf-8") as f:
            if is_new_file:
                date_header = datetime.now().strftime("%Y-%m-%d")
                f.write(f"# STRIX Daily Log — {date_header}\n\n")

            speaker = "Boss (User)" if role.lower() == "user" else "STRIX"
            f.write(f"### [{time_str}] {speaker}{link_str}\n\n{content.strip()}\n\n---\n\n")

    def get_recent_context(self, limit: int = 6) -> str:
        """
        Retrieves formatted recent context from SQLite memory or today's daily note.
        Used to inject conversation context into LLM prompts.
        """
        try:
            from memory.memory_db import get_recent_messages
            messages = get_recent_messages(limit=limit)
            if messages:
                formatted = []
                for msg in messages:
                    role_name = "User" if msg["role"].lower() == "user" else "Assistant"
                    formatted.append(f"{role_name}: {msg['content'].strip()}")
                return "\n\n".join(formatted)
        except Exception:
            pass

        note_path = self._get_today_note_path()
        if not os.path.exists(note_path):
            return ""

        try:
            with open(note_path, "r", encoding="utf-8") as f:
                content = f.read()
            blocks = content.split("---")
            recent_blocks = [b.strip() for b in blocks if b.strip()][-limit:]
            return "\n\n".join(recent_blocks)
        except Exception:
            return ""

    def read_user_profile(self) -> str:
        """Reads User Profile.md from vault if it exists."""
        profile_path = os.path.join(self.vault_path, "User Profile.md")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    def search_vault(self, query: str, max_results: int = 3) -> list:
        """Search markdown files in vault for a query string."""
        results = []
        query_lower = query.lower()

        md_files = glob.glob(os.path.join(self.vault_path, "**", "*.md"), recursive=True)
        for filepath in md_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    file_content = f.read()
                if query_lower in file_content.lower():
                    rel_path = os.path.relpath(filepath, self.vault_path)
                    results.append({
                        "file": rel_path,
                        "content": file_content[:500]
                    })
                    if len(results) >= max_results:
                        break
            except Exception:
                continue

        return results


_obsidian_memory_instance = None

def get_obsidian_memory() -> ObsidianMemoryManager:
    global _obsidian_memory_instance
    if _obsidian_memory_instance is None:
        _obsidian_memory_instance = ObsidianMemoryManager()
    return _obsidian_memory_instance
