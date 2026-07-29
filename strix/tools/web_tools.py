"""Web tools."""
from __future__ import annotations
import os
import subprocess
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

class OpenUrlTool(BaseTool):
    @property
    def name(self) -> str: return 'open_url'
    
    @property
    def description(self) -> str: return 'Open URL in browser'
    
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    
    @property
    def parameters(self) -> dict[str, Any]: return {'url': 'str', 'profile': 'str'}
    
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            params = kwargs.get('params', kwargs) if isinstance(kwargs.get('params'), dict) else kwargs
            url = str(params.get('url', ''))
            if not url:
                return ToolResult(success=False, output='', error='No URL provided.')
                
            import webbrowser
            webbrowser.open(url)
            return ToolResult(success=True, output=f'Opened {url}', error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
