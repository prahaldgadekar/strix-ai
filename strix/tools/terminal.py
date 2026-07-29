"""Terminal Tools."""
from __future__ import annotations
import subprocess
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

class TerminalTool(BaseTool):
    @property
    def name(self) -> str: return 'run_terminal'
    @property
    def description(self) -> str: return 'Run terminal command'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.MEDIUM
    @property
    def parameters(self) -> dict[str, Any]: return {'command': 'str', 'cwd': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            command = kwargs.get('command', '')
            cwd = kwargs.get('cwd', '.')
            res = subprocess.run(command, cwd=cwd, shell=True, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                return ToolResult(success=True, output=res.stdout, error=None)
            else:
                return ToolResult(success=False, output=res.stdout, error=res.stderr)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
