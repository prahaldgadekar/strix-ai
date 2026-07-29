"""Project scaffolding tools."""
from __future__ import annotations
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

class CreateJavaProjectTool(BaseTool):
    @property
    def name(self) -> str: return 'create_java_project'
    @property
    def description(self) -> str: return 'Create Java project'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.LOW
    @property
    def parameters(self) -> dict[str, Any]: return {'name': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.project_tools import create_java_project
            res = create_java_project(kwargs.get('name'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class CreateCProjectTool(BaseTool):
    @property
    def name(self) -> str: return 'create_c_project'
    @property
    def description(self) -> str: return 'Create C project'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.LOW
    @property
    def parameters(self) -> dict[str, Any]: return {'name': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.project_tools import create_c_project
            res = create_c_project(kwargs.get('name'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class CreateCppProjectTool(BaseTool):
    @property
    def name(self) -> str: return 'create_cpp_project'
    @property
    def description(self) -> str: return 'Create C++ project'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.LOW
    @property
    def parameters(self) -> dict[str, Any]: return {'name': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.project_tools import create_cpp_project
            res = create_cpp_project(kwargs.get('name'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class CreatePythonProjectTool(BaseTool):
    @property
    def name(self) -> str: return 'create_python_project'
    @property
    def description(self) -> str: return 'Create Python project'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.LOW
    @property
    def parameters(self) -> dict[str, Any]: return {'name': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.project_tools import create_python_project
            res = create_python_project(kwargs.get('name'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class ListProjectsTool(BaseTool):
    @property
    def name(self) -> str: return 'list_projects'
    @property
    def description(self) -> str: return 'List projects'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from tools.project_tools import list_projects
            res = list_projects()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
