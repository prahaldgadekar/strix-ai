from __future__ import annotations
from typing import Optional
from strix.types import (ClassifiedRequest, Context, ExecutionPlan, PlanStep,
                          StepAction, Intent, RiskLevel)
from strix.config import StrixConfig
from strix.planner.base import BasePlanner

class DirectPlanner(BasePlanner):
    """Creates a single-step execution plan for straightforward requests."""
    
    def __init__(self, config: StrixConfig):
        self.config = config
        print("[STRIX DirectPlanner] Initialized")
        
    def plan(self, request: ClassifiedRequest, context: Context) -> Optional[ExecutionPlan]:
        print(f"[STRIX DirectPlanner] Creating plan for intent: {request.intent.name}")
        
        if request.intent == Intent.MULTI_STEP:
            action = request.params.get('action')
            if action == 'work_mode':
                steps = [
                    PlanStep(id=1, action=StepAction.TOOL_CALL, target="open_app", params={"app": "vscode"}),
                    PlanStep(id=2, action=StepAction.TOOL_CALL, target="open_app", params={"app": "explorer", "path": "E:\\"}),
                    PlanStep(id=3, action=StepAction.TOOL_CALL, target="open_url", params={"url": "", "profile": "Default"}),
                ]
                return ExecutionPlan(steps=steps, risk_level=RiskLevel.SAFE, requires_approval=False)

            elif action == 'gaming_mode':
                steps = [
                    PlanStep(id=1, action=StepAction.TOOL_CALL, target="open_app", params={"app": "steam"}),
                    PlanStep(id=2, action=StepAction.TOOL_CALL, target="open_app", params={"app": "explorer", "path": r"C:\Users\prahl\OneDrive\Desktop\imp_project"}),
                ]
                return ExecutionPlan(steps=steps, risk_level=RiskLevel.SAFE, requires_approval=False)
            return None
            
        step = None
        if request.intent == Intent.TOOL_ACTION:
            step_params = dict(request.params) if request.params else {"query": request.request.raw_text}
            step = PlanStep(
                id="step_1",
                action=StepAction.TOOL_CALL,
                target=request.tool_action or "",
                params=step_params
            )
        elif request.intent == Intent.SYSTEM_COMMAND:
            step = PlanStep(
                id="step_1",
                action=StepAction.TOOL_CALL,
                target="system_command",
                params={"command": request.request.raw_text}
            )
        else:
            # CHAT/REASONING/CODING/DEV/FRONTEND/BACKEND
            target_role = request.model_role.value if request.model_role else "chat"
            step = PlanStep(
                id="step_1",
                action=StepAction.MODEL_CALL,
                target=target_role,
                params={"prompt": request.request.raw_text}
            )
            
        # Simplified risk level setting - actual lookup in approval gate
        risk_level = RiskLevel.SAFE
            
        plan = ExecutionPlan(
            steps=[step],
            risk_level=risk_level,
            requires_approval=risk_level.value >= self.config.approval_threshold
        )
        
        return plan
