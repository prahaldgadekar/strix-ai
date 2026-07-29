"""App Launcher Tool."""
from __future__ import annotations
import os
import subprocess
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

APP_MAP = {
    'chrome': 'chrome',
    'notepad': 'notepad',
    'calculator': 'calc',
    'paint': 'mspaint',
    'explorer': 'explorer',
    'vscode': 'code',
    'cmd': 'cmd',
    'powershell': 'powershell',
    'eclipse': 'eclipse',
    'pycharm': 'pycharm',
    'spotify': 'spotify',
    'discord': 'discord',
    'steam': 'steam',
}

class OpenAppTool(BaseTool):
    @property
    def name(self) -> str: return 'open_app'
    
    @property
    def description(self) -> str: return 'Open an application or folder'
    
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    
    @property
    def parameters(self) -> dict[str, Any]: return {'app': 'str', 'path': 'str'}
    
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            params = kwargs.get('params', kwargs) if isinstance(kwargs.get('params'), dict) else kwargs
            app = str(params.get('app', '')).lower()
            path = str(params.get('path', ''))
            cmd = APP_MAP.get(app, app)
            
            # Explorer / folder launching
            if app == 'explorer' or path:
                target = path if path else "E:\\"
                if not os.path.exists(target) and app == 'explorer':
                    target = "E:\\"
                subprocess.Popen(['explorer', target])
                return ToolResult(success=True, output=f'Opened Explorer at {target}, Boss.', error=None)

            # VS Code
            if app == 'vscode':
                paths = [
                    os.path.expandvars(r'%LocalAppData%\Programs\Microsoft VS Code\Code.exe'),
                    r'C:\Program Files\Microsoft VS Code\Code.exe'
                ]
                for p in paths:
                    if os.path.exists(p):
                        subprocess.Popen([p])
                        return ToolResult(success=True, output=f'Opened {app}, Boss.', error=None)

            # Steam
            if app == 'steam':
                steam_paths = [
                    r'C:\Program Files (x86)\Steam\steam.exe',
                    r'C:\Program Files\Steam\steam.exe',
                    os.path.expandvars(r'%ProgramFiles(x86)%\Steam\steam.exe'),
                    os.path.expandvars(r'%ProgramFiles%\Steam\steam.exe'),
                ]
                for p in steam_paths:
                    if os.path.exists(p):
                        subprocess.Popen([p])
                        return ToolResult(success=True, output='Opened Steam, Boss.', error=None)
                subprocess.Popen('start steam://', shell=True)
                return ToolResult(success=True, output='Opened Steam, Boss.', error=None)

            subprocess.Popen(cmd, shell=True)
            return ToolResult(success=True, output=f'Opened {app}, Boss.', error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
