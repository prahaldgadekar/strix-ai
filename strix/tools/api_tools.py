"""API Tools."""
from __future__ import annotations
from typing import Any
from strix.tools.base import BaseTool
from strix.types import RiskLevel, ToolResult
from strix.config import StrixConfig

class WeatherTool(BaseTool):
    def __init__(self, config: StrixConfig):
        self.config = config

    @property
    def name(self) -> str: return 'get_weather'
    @property
    def description(self) -> str: return 'Get weather for a city'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]:
        return {'city': {'type': 'str', 'required': False, 'default': self.config.default_city}}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.weather import format_weather
            city = kwargs.get('city', self.config.default_city)
            res = format_weather(city)
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class NewsTool(BaseTool):
    @property
    def name(self) -> str: return 'get_news'
    @property
    def description(self) -> str: return 'Get news'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'category': 'str', 'count': 'int'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.news import format_news
            res = format_news(kwargs.get('category', 'general'), kwargs.get('count', 5))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class CryptoTool(BaseTool):
    @property
    def name(self) -> str: return 'get_crypto'
    @property
    def description(self) -> str: return 'Get crypto price'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'coin': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.extras import get_crypto_price
            res = get_crypto_price(kwargs.get('coin'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class TopCryptoTool(BaseTool):
    @property
    def name(self) -> str: return 'get_top_crypto'
    @property
    def description(self) -> str: return 'Get top crypto'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.extras import get_top_crypto
            res = get_top_crypto()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class JokeTool(BaseTool):
    @property
    def name(self) -> str: return 'get_joke'
    @property
    def description(self) -> str: return 'Get a joke'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            try:
                import pyjokes
                res = pyjokes.get_joke()
            except ImportError:
                from api.extras import get_joke
                res = get_joke()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class NasaTool(BaseTool):
    @property
    def name(self) -> str: return 'get_nasa'
    @property
    def description(self) -> str: return 'Get NASA APOD'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.extras import get_nasa_apod
            res = get_nasa_apod()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class IpInfoTool(BaseTool):
    @property
    def name(self) -> str: return 'get_ip_info'
    @property
    def description(self) -> str: return 'Get IP info'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.extras import get_my_ip_info
            res = get_my_ip_info()
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class ExchangeRateTool(BaseTool):
    @property
    def name(self) -> str: return 'get_exchange'
    @property
    def description(self) -> str: return 'Get exchange rate'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'from_currency': 'str', 'to_currency': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.extras import get_exchange_rate
            res = get_exchange_rate(kwargs.get('from_currency'), kwargs.get('to_currency'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class WikipediaTool(BaseTool):
    @property
    def name(self) -> str: return 'wiki_search'
    @property
    def description(self) -> str: return 'Search wikipedia'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'query': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.extras import search_wikipedia
            res = search_wikipedia(kwargs.get('query'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))

class GitHubProfileTool(BaseTool):
    @property
    def name(self) -> str: return 'get_github'
    @property
    def description(self) -> str: return 'Get GitHub profile'
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    @property
    def parameters(self) -> dict[str, Any]: return {'username': 'str'}
    def execute(self, **kwargs: Any) -> ToolResult:
        try:
            from api.extras import get_github_profile
            res = get_github_profile(kwargs.get('username'))
            return ToolResult(success=True, output=str(res), error=None)
        except Exception as e:
            return ToolResult(success=False, output='', error=str(e))
