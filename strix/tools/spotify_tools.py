"""Spotify Tools."""
from __future__ import annotations
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult

class PlaySpotifyTool(BaseTool):
    @property
    def name(self) -> str: return 'play_spotify'
    @property
    def description(self) -> str: return 'Play song'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'query': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from spotify_controller import play_song
            res = play_song(kwargs.get('query'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class PlayPlaylistTool(BaseTool):
    @property
    def name(self) -> str: return 'play_playlist'
    @property
    def description(self) -> str: return 'Play playlist'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'name': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from spotify_controller import play_playlist
            res = play_playlist(kwargs.get('name'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class MusicPauseTool(BaseTool):
    @property
    def name(self) -> str: return 'music_pause'
    @property
    def description(self) -> str: return 'Pause music'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from spotify_controller import pause_music
            res = pause_music()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class MusicNextTool(BaseTool):
    @property
    def name(self) -> str: return 'music_next'
    @property
    def description(self) -> str: return 'Next track'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from spotify_controller import next_track
            res = next_track()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class MusicPrevTool(BaseTool):
    @property
    def name(self) -> str: return 'music_prev'
    @property
    def description(self) -> str: return 'Previous track'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from spotify_controller import prev_track
            res = prev_track()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class MusicStopTool(BaseTool):
    @property
    def name(self) -> str: return 'music_stop'
    @property
    def description(self) -> str: return 'Stop music'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from spotify_controller import stop_music
            res = stop_music()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class PlayRandomSongTool(BaseTool):
    @property
    def name(self) -> str: return 'play_random_song'
    @property
    def description(self) -> str: return 'Play a random song from playlist'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from spotify_controller import play_random_song
            res = play_random_song()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
