"""
strix/planner/base.py — Planner Interface
===========================================
Abstract base class for all planners.
Implementations: DirectPlanner (single-step), LLMPlanner (multi-step via DeepSeek-R1).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from strix.types import ClassifiedRequest, Context, ExecutionPlan


class BasePlanner(ABC):
    """
    Abstract interface for execution planners.

    A planner takes a classified request and produces an ExecutionPlan —
    a sequence of PlanSteps with dependency ordering.

    Plugin contract:
        - Implement plan() to return an ExecutionPlan
        - DirectPlanner handles single-step (90% of requests)
        - LLMPlanner handles multi-step decomposition via reasoning model
    """

    @abstractmethod
    def plan(
        self,
        request: ClassifiedRequest,
        context: Context,
    ) -> ExecutionPlan:
        """
        Create an execution plan for the classified request.

        Args:
            request: The classified request with intent and routing info.
            context: Assembled context including conversation history.

        Returns:
            ExecutionPlan with ordered steps, risk level, and approval flag.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name of this planner."""
        return self.__class__.__name__
