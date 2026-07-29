"""
strix/models/base.py — Model Provider Interface
=================================================
Abstract base class for all LLM providers.
Implementations: OllamaProvider (local), CloudProvider (optional fallback).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator

from strix.types import ModelOptions


class BaseModelProvider(ABC):
    """
    Abstract interface for LLM model providers.

    A provider wraps a specific model backend (Ollama, cloud API, etc.)
    and exposes a uniform generate() interface.

    Plugin contract:
        - Implement generate() for text generation (streaming + non-streaming)
        - Implement is_available() for health checks
        - Implement name property for identification
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: str = "",
        options: ModelOptions | None = None,
        stream: bool = False,
    ) -> str | Generator[str, None, None]:
        """
        Generate text from the model.

        Args:
            prompt: The user/context prompt.
            system: Optional system prompt.
            options: Model-specific generation options.
            stream: If True, return a token generator instead of full string.

        Returns:
            Complete response string, or a generator yielding tokens.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this model provider is reachable and ready."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this provider (e.g. 'gemma3:4b via Ollama')."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """The model identifier (e.g. 'gemma3:4b')."""
        ...
