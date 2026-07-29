"""
strix/config.py — Centralized Configuration
=============================================
Single source of truth for all Strix settings.
Loads from .env file and provides typed access to every config value.
Replaces scattered os.getenv() calls across 6+ legacy files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore


# ── Paths ─────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent  # e:\Strix
ENV_PATH = ROOT_DIR / ".env"


def _load_env() -> None:
    """Load .env from project root."""
    if load_dotenv and ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)


def _env(key: str, default: str = "") -> str:
    """Get env var with fallback."""
    return os.getenv(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    """Get boolean env var."""
    val = os.getenv(key, "").lower().strip()
    if not val:
        return default
    return val in ("true", "1", "yes", "on")


def _env_int(key: str, default: int = 0) -> int:
    """Get integer env var."""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


# ── Risk level mapping ────────────────────────────────────────

_RISK_MAP = {
    "safe": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass
class StrixConfig:
    """
    Centralized configuration for all Strix components.

    Usage:
        config = StrixConfig.load()
        model = config.chat_model  # "qwen3:8b"
    """

    # ── Model assignments ─────────────────────────────────────
    classifier_model: str = "gemma3:4b"
    chat_model: str = "qwen3:8b"
    reasoning_model: str = "deepseek-r1:7b"
    coding_model: str = "qwen2.5-coder:latest"
    planning_model: str = "deepseek-r1:7b"
    summarizer_model: str = "gemma3:4b"

    # ── Ollama ────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"

    # ── API keys ──────────────────────────────────────────────
    weather_api_key: str = ""
    news_api_key: str = ""
    nasa_api_key: str = ""
    github_token: str = ""
    github_username: str = "prahaldgadekar"

    # ── Spotify ───────────────────────────────────────────────
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8888/callback"

    # ── Behavior ──────────────────────────────────────────────
    approval_threshold: int = 2           # RiskLevel.MEDIUM
    max_context_tokens: int = 4096
    enable_code_validation: bool = True
    enable_cloud_fallback: bool = False
    default_city: str = "pune"

    # ── Cloud fallback (optional) ─────────────────────────────
    cloud_provider: str = ""
    cloud_api_key: str = ""
    cloud_model: str = ""

    # ── Paths ─────────────────────────────────────────────────
    root_dir: Path = field(default_factory=lambda: ROOT_DIR)
    memory_db_path: Path = field(
        default_factory=lambda: ROOT_DIR / "memory" / "strix_memory.db"
    )

    # ── Chrome profiles ───────────────────────────────────────
    gmail_main: str = ""
    gmail_work: str = ""

    @classmethod
    def load(cls) -> "StrixConfig":
        """Load configuration from .env file and environment variables."""
        _load_env()

        return cls(
            # Models
            classifier_model=_env("CLASSIFIER_MODEL", "gemma3:4b"),
            chat_model=_env("CHAT_MODEL", "qwen3:8b"),
            reasoning_model=_env("REASONING_MODEL", "deepseek-r1:7b"),
            coding_model=_env("CODING_MODEL", "qwen3-coder:8b"),
            planning_model=_env("PLANNING_MODEL", "deepseek-r1:7b"),
            summarizer_model=_env("SUMMARIZER_MODEL", "gemma3:4b"),

            # Ollama
            ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),

            # API Keys
            weather_api_key=_env("OPENWEATHER_API_KEY"),
            news_api_key=_env("NEWS_API_KEY"),
            nasa_api_key=_env("NASA_KEY"),
            github_token=_env("GITHUB_TOKEN"),
            github_username=_env("GITHUB_USERNAME", "prahaldgadekar"),

            # Spotify
            spotify_client_id=_env("SPOTIFY_CLIENT_ID"),
            spotify_client_secret=_env("SPOTIFY_CLIENT_SECRET"),
            spotify_redirect_uri=_env("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),

            # Behavior
            approval_threshold=_RISK_MAP.get(
                _env("APPROVAL_THRESHOLD", "medium").lower(), 2
            ),
            max_context_tokens=_env_int("MAX_CONTEXT_TOKENS", 4096),
            enable_code_validation=_env_bool("ENABLE_CODE_VALIDATION", True),
            enable_cloud_fallback=_env_bool("ENABLE_CLOUD_FALLBACK", False),
            default_city=_env("DEFAULT_CITY", "pune"),

            # Cloud fallback
            cloud_provider=_env("CLOUD_PROVIDER"),
            cloud_api_key=_env("CLOUD_API_KEY"),
            cloud_model=_env("CLOUD_MODEL"),

            # Paths
            root_dir=ROOT_DIR,
            memory_db_path=ROOT_DIR / "memory" / "strix_memory.db",

            # Chrome
            gmail_main=_env("GMAIL_MAIN"),
            gmail_work=_env("GMAIL_WORK"),
        )

    def get_model_for_role(self, role: str) -> str:
        """Get the model name assigned to a role string."""
        role_map = {
            "classifier": self.classifier_model,
            "chat": self.chat_model,
            "reasoning": self.reasoning_model,
            "coding": self.coding_model,
            "planning": self.planning_model,
            "summarizer": self.summarizer_model,
        }
        return role_map.get(role, self.chat_model)

    def __repr__(self) -> str:
        return (
            f"StrixConfig(\n"
            f"  classifier={self.classifier_model}, chat={self.chat_model},\n"
            f"  reasoning={self.reasoning_model}, coding={self.coding_model},\n"
            f"  ollama={self.ollama_base_url}\n"
            f")"
        )
