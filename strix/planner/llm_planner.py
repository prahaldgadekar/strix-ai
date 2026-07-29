"""
strix/planner/llm_planner.py — Multi-Step LLM Planner & PlannerChain
====================================================================
Uses DeepSeek-R1 (or configured PLANNING / REASONING model) to decompose
complex, multi-step user requests into structured ExecutionPlans.

Includes PlannerChain to seamlessly route single-step requests through
DirectPlanner (fast path) and multi-step requests through LLMPlanner (slow path).
"""

from __future__ import annotations

import json
import re
from typing import Optional

from strix.config import StrixConfig
from strix.models.base import BaseModelProvider
from strix.planner.base import BasePlanner
from strix.planner.direct_planner import DirectPlanner
from strix.types import (
    ClassifiedRequest,
    Context,
    ExecutionPlan,
    Intent,
    ModelOptions,
    ModelRole,
    PlanStep,
    REASON_OPTIONS,
    RiskLevel,
    StepAction,
)


PLANNER_SYSTEM_PROMPT = """You are the Lead Task Planner for STRIX, a local-first AI assistant.
Your job is to break down complex user requests into a clean, step-by-step execution plan in JSON format.

Available Step Actions:
1. "tool_call": Invoke a deterministic tool. Target must be a valid tool name (e.g. "open_app", "get_weather", "create_desktop_file", "search_files", "run_terminal", "run_oi_task").
2. "model_call": Invoke an LLM for text/code generation or reasoning. Target must be a model role ("chat", "reasoning", "coding").
3. "validate": Validate generated code syntax before returning.

Output Requirements:
Return strictly a JSON object with this exact schema:
{
  "steps": [
    {
      "id": 1,
      "action": "tool_call",
      "target": "get_weather",
      "params": {"city": "pune"},
      "depends_on": []
    },
    {
      "id": 2,
      "action": "model_call",
      "target": "chat",
      "params": {"prompt": "Summarize the weather data"},
      "depends_on": [1]
    }
  ],
  "requires_approval": false,
  "risk_level": "safe",
  "estimated_model": "reasoning"
}

Risk levels: "safe", "low", "medium", "high", "critical".
DO NOT wrap output in markdown unless standard JSON. Respond with valid JSON only."""


class LLMPlanner(BasePlanner):
    """
    Multi-step planner powered by LLM reasoning (DeepSeek-R1 / PLANNING model).
    Used when intent is Intent.MULTI_STEP or when complex task decomposition is needed.
    """

    def __init__(self, config: StrixConfig, model_registry=None):
        self.config = config
        self.model_registry = model_registry
        print("[STRIX LLMPlanner] Initialized")

    def _get_provider() -> Optional[BaseModelProvider]:
        if self.model_registry:
            return self.model_registry.get(ModelRole.PLANNING)
        return None

    def plan(self, request: ClassifiedRequest, context: Context) -> ExecutionPlan:
        raw_text = request.request.raw_text
        print(f"[STRIX LLMPlanner] Decomposing complex request: '{raw_text}'")

        if not self.model_registry:
            print("[STRIX LLMPlanner] No model registry available, falling back to direct plan")
            return self._fallback_plan(request, context)

        provider = self.model_registry.get(ModelRole.PLANNING)
        prompt = (
            f"User Request: {raw_text}\n"
            f"Intent: {request.intent.value}\n"
            f"Available parameters: {json.dumps(request.params)}\n\n"
            f"Generate a step-by-step execution plan JSON."
        )

        try:
            response_text = provider.generate(
                prompt=prompt,
                system=PLANNER_SYSTEM_PROMPT,
                options=REASON_OPTIONS,
                stream=False,
            )

            if isinstance(response_text, str):
                plan = self._parse_json_plan(response_text, request)
                if plan:
                    return plan
        except Exception as e:
            print(f"[STRIX LLMPlanner] Generation/parsing error: {e}")

        return self._fallback_plan(request, context)

    def _parse_json_plan(self, text: str, request: ClassifiedRequest) -> Optional[ExecutionPlan]:
        """Extract and parse JSON execution plan from LLM response."""
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            return None

        try:
            data = json.loads(json_match.group(0))
            raw_steps = data.get("steps", [])
            steps: list[PlanStep] = []

            for s in raw_steps:
                action_str = s.get("action", "model_call").lower()
                try:
                    action = StepAction(action_str)
                except ValueError:
                    action = StepAction.MODEL_CALL if "model" in action_str else StepAction.TOOL_CALL

                step = PlanStep(
                    id=int(s.get("id", len(steps) + 1)),
                    action=action,
                    target=str(s.get("target", "chat")),
                    params=dict(s.get("params", {})),
                    depends_on=[int(d) for d in s.get("depends_on", [])],
                )
                steps.append(step)

            if not steps:
                return None

            risk_str = str(data.get("risk_level", "low")).lower()
            try:
                risk_level = RiskLevel(risk_str)
            except ValueError:
                risk_level = RiskLevel.LOW

            requires_approval = data.get(
                "requires_approval",
                risk_level.value >= self.config.approval_threshold,
            )

            est_model_str = str(data.get("estimated_model", "reasoning")).lower()
            try:
                est_model = ModelRole(est_model_str)
            except ValueError:
                est_model = ModelRole.REASONING

            print(f"[STRIX LLMPlanner] Generated {len(steps)}-step plan (risk={risk_level.name})")
            return ExecutionPlan(
                steps=steps,
                requires_approval=requires_approval,
                risk_level=risk_level,
                estimated_model=est_model,
            )
        except Exception as e:
            print(f"[STRIX LLMPlanner] JSON parse error: {e}")
            return None

    def _fallback_plan(self, request: ClassifiedRequest, context: Context) -> ExecutionPlan:
        """Fallback to single-step plan if LLM decomposition fails."""
        dp = DirectPlanner(self.config)
        return dp.plan(request, context)


class PlannerChain(BasePlanner):
    """
    Chains DirectPlanner (fast path, 1-step) and LLMPlanner (slow path, multi-step).
    Single-step tool actions, chat, code, and reasoning go through DirectPlanner.
    Intent.MULTI_STEP and explicit workflow requests go through LLMPlanner.
    """

    def __init__(self, direct_planner: DirectPlanner, llm_planner: LLMPlanner):
        self.direct_planner = direct_planner
        self.llm_planner = llm_planner
        print("[STRIX PlannerChain] Initialized")

    def plan(self, request: ClassifiedRequest, context: Context) -> ExecutionPlan:
        # Try direct planner fast path first (handles work_mode and gaming_mode)
        direct_plan = self.direct_planner.plan(request, context)
        if direct_plan is not None:
            return direct_plan

        if request.intent == Intent.MULTI_STEP:
            print("[STRIX PlannerChain] Multi-step intent detected -> Routing to LLMPlanner")
            return self.llm_planner.plan(request, context)

        print("[STRIX PlannerChain] Routing to DirectPlanner (fast path)")
        return direct_plan
