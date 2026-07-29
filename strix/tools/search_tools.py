"""Search Tools."""
from __future__ import annotations
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

class SearchFilesTool(BaseTool):
    @property
    def name(self) -> str: return 'search_files'
    @property
    def description(self) -> str: return 'Search files'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'query': 'str', 'search_path': 'str', 'extensions': 'list'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.search_tools import search_files, format_search_results
            res = search_files(kwargs.get('query'), kwargs.get('search_path'), kwargs.get('extensions'))
            formatted = format_search_results(res)
            return ToolResult(success=True, output=str(formatted), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class ReadFileTool(BaseTool):
    @property
    def name(self) -> str: return 'read_file'
    @property
    def description(self) -> str: return 'Read a file'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'path': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.search_tools import read_file
            res = read_file(kwargs.get('path'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class DirectoryTreeTool(BaseTool):
    @property
    def name(self) -> str: return 'directory_tree'
    @property
    def description(self) -> str: return 'Get directory tree'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'path': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.search_tools import get_directory_tree
            res = get_directory_tree(kwargs.get('path'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
