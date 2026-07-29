"""
strix/tools/oi_tool.py — Open Interpreter Autonomous Tool
==========================================================
Wraps oi_runner.py to enable STRIX to execute autonomous multi-step code tasks
and file creation commands using Open Interpreter or Ollama direct fallbacks.
"""

from __future__ import annotations

from typing import Dict, Any

from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

try:
    from oi_runner import create_file_with_code, run_oi_task
except ImportError:
    create_file_with_code = None  # type: ignore
    run_oi_task = None  # type: ignore


class OpenInterpreterTool(BaseTool):
    """
    Tool for autonomous code creation and execution via Open Interpreter / Ollama.
    """

    @property
    def name(self) -> str:
        return "run_oi_task"

    @property
    def description(self) -> str:
        return "Run autonomous code generation or multi-step developer task using Open Interpreter."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @property
    def parameters(self) -> dict:
        return {
            "prompt": {
                "type": "string",
                "required": True,
                "description": "Natural language developer prompt (e.g. 'create a python file called app.py')",
            },
            "action": {
                "type": "string",
                "required": False,
                "default": "create_file",
                "description": "Action type: 'create_file' or 'execute_task'",
            },
        }

    def execute(self, params: dict) -> ToolResult:
        prompt = params.get("prompt", "")
        action = params.get("action", "create_file")

        if not prompt:
            return ToolResult(success=False, output="", error="Missing 'prompt' parameter.")

        try:
            if action == "create_file" and create_file_with_code:
                output = create_file_with_code(prompt)
                return ToolResult(success=True, output=str(output))
            elif run_oi_task:
                output = run_oi_task(prompt)
                return ToolResult(success=True, output=str(output))
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error="Open Interpreter (oi_runner) module is not available.",
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Open Interpreter error: {e}")
