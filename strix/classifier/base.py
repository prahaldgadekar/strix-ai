"""
strix/classifier/base.py — Classifier Interface
==================================================
Abstract base class for all intent classifiers.
Implementations: RuleClassifier (keyword), LLMClassifier (Gemma 3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from strix.types import ClassifiedRequest, Context, StrixRequest


class BaseClassifier(ABC):
    """
    Abstract interface for intent classification.

    A classifier takes a raw StrixRequest and determines:
    - What the user wants (Intent enum)
    - Which model should handle it (ModelRole enum)
    - Whether it's a tool action (tool name + params)
    - How confident the classification is (0.0 to 1.0)

    Plugin contract:
        - Implement classify() to return a ClassifiedRequest
        - Return confidence < 0.7 to signal uncertainty (triggers fallback)
    """

    @abstractmethod
    def classify(
        self,
        request: StrixRequest,
        context: Context | None = None,
    ) -> ClassifiedRequest:
        """
        Classify user intent and determine routing.

        Args:
            request: The raw user request.
            context: Optional conversation context for disambiguation.

        Returns:
            ClassifiedRequest with intent, model_role, tool_action, params, confidence.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name of this classifier."""
        return self.__class__.__name__
