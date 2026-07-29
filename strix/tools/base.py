"""Base tool interface for Strix."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from strix.types import RiskLevel, ToolResult

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def risk_level(self) -> RiskLevel:
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        ...
