"""System monitoring tools."""
from __future__ import annotations
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult
from tools.system_tools import get_system_summary

class SystemStatusTool(BaseTool):
    @property
    def name(self) -> str: return "get_system_status"
    
    @property
    def description(self) -> str: return "Gets the system status summary."
    
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    
    @property
    def parameters(self) -> dict[str, Any]: return {}
    
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            output = get_system_summary()
            return ToolResult(success=True, output=str(output), error=None)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
