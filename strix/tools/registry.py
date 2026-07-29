"""Tool Registry for Strix."""
from __future__ import annotations
import json
from strix.config import StrixConfig
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_all(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level.name if hasattr(t.risk_level, 'name') else str(t.risk_level),
                "parameters": t.parameters,
            }
            for t in self._tools.values()
        ]

    def get_schema_for_llm(self) -> str:
        schema = []
        for t in self._tools.values():
            schema.append(f"Tool: {t.name}\nDescription: {t.description}\nParams: {json.dumps(t.parameters)}")
        return "\n\n".join(schema)

    def register_defaults(self, config: StrixConfig) -> None:
        from strix.tools.system_tools import SystemStatusTool
        from strix.tools.api_tools import (
            WeatherTool, NewsTool, CryptoTool, TopCryptoTool,
            JokeTool, NasaTool, IpInfoTool, ExchangeRateTool,
            WikipediaTool, GitHubProfileTool
        )
        from strix.tools.filesystem import (
            CreateDesktopFileTool, CreateDesktopFolderTool,
            DeleteDesktopFileTool, ListDesktopTool
        )
        from strix.tools.app_launcher import OpenAppTool
        from strix.tools.web_tools import OpenUrlTool
        from strix.tools.search_tools import SearchFilesTool, ReadFileTool, DirectoryTreeTool
        from strix.tools.project_tools import (
            CreateJavaProjectTool, CreateCProjectTool,
            CreateCppProjectTool, CreatePythonProjectTool, ListProjectsTool
        )
        from strix.tools.spotify_tools import (
            PlaySpotifyTool, PlayPlaylistTool, PlayRandomSongTool,
            MusicPauseTool, MusicNextTool, MusicPrevTool, MusicStopTool
        )
        from strix.tools.terminal import TerminalTool
        from strix.tools.git_tools import GitStatusTool, GitLogTool, GitDiffTool
        from strix.tools.oi_tool import OpenInterpreterTool

        default_tools = [
            SystemStatusTool(),
            WeatherTool(config), NewsTool(), CryptoTool(), TopCryptoTool(),
            JokeTool(), NasaTool(), IpInfoTool(), ExchangeRateTool(),
            WikipediaTool(), GitHubProfileTool(),
            CreateDesktopFileTool(), CreateDesktopFolderTool(),
            DeleteDesktopFileTool(), ListDesktopTool(),
            OpenAppTool(),
            OpenUrlTool(),
            SearchFilesTool(), ReadFileTool(), DirectoryTreeTool(),
            CreateJavaProjectTool(), CreateCProjectTool(),
            CreateCppProjectTool(), CreatePythonProjectTool(), ListProjectsTool(),
            PlaySpotifyTool(), PlayPlaylistTool(), PlayRandomSongTool(), MusicPauseTool(),
            MusicNextTool(), MusicPrevTool(), MusicStopTool(),
            TerminalTool(),
            GitStatusTool(), GitLogTool(), GitDiffTool(),
            OpenInterpreterTool()
        ]

        for t in default_tools:
            self.register(t)
            
        print(f"[STRIX ToolRegistry] Registered {len(self._tools)} tools")
