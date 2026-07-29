"""Git tools."""
from __future__ import annotations
import subprocess
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

class GitStatusTool(BaseTool):
    @property
    def name(self) -> str: return 'git_status'
    @property
    def description(self) -> str: return 'Git status'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'path': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            path = kwargs.get('path', '.')
            res = subprocess.run(['git', 'status'], cwd=path, capture_output=True, text=True)
            if res.returncode == 0:
                return ToolResult(success=True, output=res.stdout, error=None)
            return ToolResult(success=False, output=res.stdout, error=res.stderr)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class GitLogTool(BaseTool):
    @property
    def name(self) -> str: return 'git_log'
    @property
    def description(self) -> str: return 'Git log'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'path': 'str', 'count': 'int'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            path = kwargs.get('path', '.')
            count = kwargs.get('count', 5)
            res = subprocess.run(['git', 'log', '--oneline', f'-{count}'], cwd=path, capture_output=True, text=True)
            if res.returncode == 0:
                return ToolResult(success=True, output=res.stdout, error=None)
            return ToolResult(success=False, output=res.stdout, error=res.stderr)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class GitDiffTool(BaseTool):
    @property
    def name(self) -> str: return 'git_diff'
    @property
    def description(self) -> str: return 'Git diff'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'path': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            path = kwargs.get('path', '.')
            res = subprocess.run(['git', 'diff'], cwd=path, capture_output=True, text=True)
            if res.returncode == 0:
                return ToolResult(success=True, output=res.stdout, error=None)
            return ToolResult(success=False, output=res.stdout, error=res.stderr)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
