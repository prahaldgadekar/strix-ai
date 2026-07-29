"""Filesystem tools."""
from __future__ import annotations
import os
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')

class CreateDesktopFileTool(BaseTool):
    @property
    def name(self) -> str: return 'create_desktop_file'
    @property
    def description(self) -> str: return 'Create file on desktop'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.LOW
    @property
    def parameters(self) -> dict[str, Any]: return {'filename': 'str', 'content': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            filename = kwargs.get('filename', '')
            content = kwargs.get('content', '')
            path = os.path.join(DESKTOP, filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return ToolResult(success=True, output=f'Created {filename}', error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class CreateDesktopFolderTool(BaseTool):
    @property
    def name(self) -> str: return 'create_desktop_folder'
    @property
    def description(self) -> str: return 'Create folder on desktop'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.LOW
    @property
    def parameters(self) -> dict[str, Any]: return {'foldername': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            foldername = kwargs.get('foldername', '')
            path = os.path.join(DESKTOP, foldername)
            os.makedirs(path, exist_ok=True)
            return ToolResult(success=True, output=f'Created folder {foldername}', error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class DeleteDesktopFileTool(BaseTool):
    @property
    def name(self) -> str: return 'delete_desktop_file'
    @property
    def description(self) -> str: return 'Delete file on desktop'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.HIGH
    @property
    def parameters(self) -> dict[str, Any]: return {'filename': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            filename = kwargs.get('filename', '')
            path = os.path.join(DESKTOP, filename)
            if os.path.exists(path):
                os.remove(path)
                return ToolResult(success=True, output=f'Deleted {filename}', error=None)
            return ToolResult(success=False, output='', error='File not found')
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class ListDesktopTool(BaseTool):
    @property
    def name(self) -> str: return 'list_desktop'
    @property
    def description(self) -> str: return 'List desktop contents'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            contents = os.listdir(DESKTOP)
            return ToolResult(success=True, output=str(contents), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
