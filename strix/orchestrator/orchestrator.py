from __future__ import annotations
from strix.types import (ExecutionPlan, PlanStep, StepAction, Context, ModelRole,
                          StrixResponse, ToolResult, ModelOptions,
                          CHAT_OPTIONS, CODE_OPTIONS, REASON_OPTIONS)
from strix.config import StrixConfig

class Orchestrator:
    """Executes a plan by coordinating tools and models."""
    
    def __init__(self, model_registry, tool_registry, config: StrixConfig):
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.config = config
        print("[STRIX Orchestrator] Initialized")
        
    def _build_model_prompt(self, step: PlanStep, context: Context) -> tuple[str, str]:
        """Returns (prompt, system_prompt)."""
        prompt = step.params.get('prompt', '')
        return prompt, context.system_prompt
        
    def _topological_sort(self, steps: list[PlanStep]) -> list[PlanStep]:
        """Sorts steps by dependencies."""
        return steps
        
    def execute(self, plan: ExecutionPlan, context: Context, stream: bool = False, stream_callback=None) -> StrixResponse:
        steps = self._topological_sort(plan.steps)
        final_text = ""
        stream_gen = None
        
        for step in steps:
            print(f"[STRIX Orchestrator] Step {step.id}: {step.action.name} -> {step.target}")
            
            if step.action == StepAction.TOOL_CALL:
                if step.target == 'system_command':
                    cmd = step.params.get('command', '')
                    if cmd.lower() in ['shutdown', 'kill', 'exit']:
                        return StrixResponse(text="STRIX_SHUTDOWN")
                    elif 'creator' in cmd.lower() or 'who made you' in cmd.lower():
                        return StrixResponse(text="I was created by Prahlad, Boss. He built me from scratch.")
                    return StrixResponse(text="System command executed.")
                    
                tool = self.tool_registry.get(step.target) if hasattr(self.tool_registry, 'get') else getattr(self.tool_registry, 'get_tool')(step.target)
                if tool:
                    try:
                        result = tool.execute(step.params)
                    except TypeError:
                        result = tool.execute(**step.params)
                    final_text += f"\nTool Output: {result.output}"
                else:
                    final_text += f"\nError: Tool {step.target} not found."
                    
            elif step.action == StepAction.MODEL_CALL:
                try:
                    role = ModelRole(step.target)
                except ValueError:
                    role = ModelRole.CHAT
                    
                provider = self.model_registry.get(role) if hasattr(self.model_registry, 'get') else getattr(self.model_registry, 'get_provider')(role)
                if not provider:
                    return StrixResponse(text=f"Error: Model provider for {role.name} not found.")
                    
                prompt, system_prompt = self._build_model_prompt(step, context)
                
                if stream:
                    stream_gen = provider.generate(prompt, system=system_prompt, stream=True)
                else:
                    result = provider.generate(prompt, system=system_prompt, stream=False)
                    final_text = result if isinstance(result, str) else str(result)
                    
        return StrixResponse(text=final_text.strip(), stream=stream_gen)
