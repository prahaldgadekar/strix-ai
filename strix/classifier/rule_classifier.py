"""
Rule-Based Classifier
FAST path — zero LLM calls, pure keyword matching.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List

from strix.types import Intent, ModelRole, ClassifiedRequest, StrixRequest, Context
from strix.config import StrixConfig
from strix.classifier.base import BaseClassifier

class RuleClassifier(BaseClassifier):
    def __init__(self, config: StrixConfig):
        self.config = config
        self.wake_words = ["hey jarvis", "jarvis", "strix", "hey strix"]
        self.speech_fixes = {
            "clothes": "close",
            "quit ": "quit ",
            "open calm": "open chrome",
        }
        self.app_map = {
            "chrome": "chrome",
            "notepad": "notepad",
            "calculator": "calc",
            "vscode": "code",
            "cmd": "cmd",
            "powershell": "powershell",
            "spotify": "spotify",
            "discord": "discord"
        }
        self.url_map = {
            "youtube": "https://youtube.com",
            "github": "https://github.com",
            "chatgpt": "https://chat.openai.com",
            "gmail": "https://mail.google.com",
            "gemini": "https://gemini.google.com"
        }

    def _has(self, text: str, words: List[str]) -> bool:
        tl = text.lower()
        return any(w in tl for w in words)
        
    def _strip_wake_word(self, text: str) -> str:
        tl = text.lower().strip()
        for ww in self.wake_words:
            if tl.startswith(ww):
                return tl[len(ww):].strip()
        return tl

    def _edit_dist(self, s1: str, s2: str) -> int:
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        distances = range(len(s1) + 1)
        for i2, c2 in enumerate(s2):
            distances_ = [i2+1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        return distances[-1]

    def _fuzzy_app_fix(self, text: str) -> str:
        words = text.split()
        if not words: return text
        if words[0] in ["open", "launch", "start"] and len(words) > 1:
            target = " ".join(words[1:])
            for app in self.app_map:
                if self._edit_dist(target, app) <= 2:
                    return f"{words[0]} {app}"
        return text

    def _web_name_fix(self, text: str) -> str:
        words = text.split()
        if not words: return text
        if words[0] in ["open", "go"] and len(words) > 1:
            if words[0] == "go" and len(words) > 2 and words[1] == "to":
                target = " ".join(words[2:])
            else:
                target = " ".join(words[1:])
            for site in self.url_map:
                if self._edit_dist(target, site) <= 2:
                    return text.replace(target, site)
        return text

    def _fix_speech(self, text: str) -> str:
        tl = text.lower()
        for bad, good in self.speech_fixes.items():
            tl = tl.replace(bad, good)
        tl = self._fuzzy_app_fix(tl)
        tl = self._web_name_fix(tl)
        return tl

    def classify(self, request: StrixRequest, context: Optional[Context] = None) -> ClassifiedRequest:
        text = self._strip_wake_word(request.raw_text)
        text = self._fix_speech(text)
        tl = text.lower()
        
        print(f"[STRIX RuleClassifier] Processing: '{tl}'")

        # System commands
        if self._has(tl, ["kill", "self destruct", "delete yourself"]):
            return ClassifiedRequest(request=request, intent=Intent.SYSTEM_COMMAND, model_role=ModelRole.CHAT, confidence=1.0, params={'action': 'kill'})
        if self._has(tl, ["shutdown", "shut down", "exit", "quit", "turn off", "sleep"]):
            return ClassifiedRequest(request=request, intent=Intent.SYSTEM_COMMAND, model_role=ModelRole.CHAT, confidence=1.0, params={'action': 'shutdown'})
        if self._has(tl, ["who made you", "who created you"]):
            return ClassifiedRequest(request=request, intent=Intent.SYSTEM_COMMAND, model_role=ModelRole.CHAT, confidence=1.0, params={'action': 'creator'})

        # Tool actions
        if self._has(tl, ["weather", "temperature", "rain"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_weather")
        if self._has(tl, ["news", "headline"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_news")
        if self._has(tl, ["system status", "system report", "cpu usage", "ram usage", "ram status", "ram info"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_system_status")
        if self._has(tl, ["tell me a joke"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_joke")
        if self._has(tl, ["nasa apod"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_nasa")
        if self._has(tl, ["my ip", "ip address"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_ip_info")
        if self._has(tl, ["bitcoin", "ethereum"]):
            coin = "bitcoin" if "bitcoin" in tl else "ethereum"
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_crypto", params={"coin": coin})
        if self._has(tl, ["exchange rate"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_exchange")
        if self._has(tl, ["github profile"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="get_github")
        if self._has(tl, ["list desktop"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="list_desktop")
        if self._has(tl, ["search for", "find file"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="search_files")

        # App launches
        if tl.startswith(("open ", "launch ", "start ")):
            for prefix in ["open ", "launch ", "start "]:
                if tl.startswith(prefix):
                    target = tl[len(prefix):].strip()
                    if target in self.app_map:
                        return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="open_app", params={"app": self.app_map[target]})
        
        # URL opens
        if tl.startswith(("open ", "go to ")):
            for prefix in ["open ", "go to "]:
                if tl.startswith(prefix):
                    target = tl[len(prefix):].strip()
                    if target in self.url_map:
                        return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="open_url", params={"url": self.url_map[target], "profile": "default"})

        # Anime sites & Work/Gaming modes (checked before generic music play)
        if self._has(tl, ["play some anime", "watch anime", "show anime", "open anime", "play anime", "miruro"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="open_url", params={"url": "https://www.miruro.to/", "profile": "main"})
            
        if self._has(tl, ["show my sites", "show my site", "my sites", "everythingmoe", "anime list"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="open_url", params={"url": "https://everythingmoe.com/", "profile": "main"})

        if self._has(tl, ["start working", "work time", "work mode", "dev mode", "coding time"]):
            return ClassifiedRequest(request=request, intent=Intent.MULTI_STEP, model_role=ModelRole.CHAT, confidence=1.0, params={'action': 'work_mode'})

        if self._has(tl, ["start gaming mode", "gaming mode", "game mode", "game time", "start game mode"]):
            return ClassifiedRequest(request=request, intent=Intent.MULTI_STEP, model_role=ModelRole.CHAT, confidence=1.0, params={'action': 'gaming_mode'})

        # Music
        if self._has(tl, ["play some song", "play a song", "play random song", "play a random song", "play some music", "play random music", "play something", "play random track", "play random"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="play_random_song")
        if self._has(tl, ["playlist"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="play_playlist")
        if tl.startswith("play "):
            song = tl[5:].strip()
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="play_spotify", params={"query": song})
        if self._has(tl, ["music pause", "pause music"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="music_pause")
        if self._has(tl, ["music next", "next song"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="music_next")
        if self._has(tl, ["music prev", "previous song"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="music_prev")
        if self._has(tl, ["music stop", "stop music"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=1.0, tool_action="music_stop")

        # File operations
        if self._has(tl, ["create file on desktop"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=0.9, tool_action="create_desktop_file")
        if self._has(tl, ["create folder on desktop"]):
            return ClassifiedRequest(request=request, intent=Intent.TOOL_ACTION, model_role=ModelRole.CHAT, confidence=0.9, tool_action="create_desktop_folder")

        # Code requests
        if self._has(tl, ["html", "css", "react"]) and self._has(tl, ["write", "create"]):
            return ClassifiedRequest(request=request, intent=Intent.FRONTEND, model_role=ModelRole.CODING, confidence=0.85)
        if self._has(tl, ["api", "server", "django", "flask"]) and self._has(tl, ["write", "create"]):
            return ClassifiedRequest(request=request, intent=Intent.BACKEND, model_role=ModelRole.CODING, confidence=0.85)
        if self._has(tl, ["fix this", "debug", "boilerplate"]):
            return ClassifiedRequest(request=request, intent=Intent.DEV, model_role=ModelRole.CODING, confidence=0.85)
        if self._has(tl, ["write code", "python", "javascript", "java", "script", "function", "program", "code for", "write a"]):
            return ClassifiedRequest(request=request, intent=Intent.CODING, model_role=ModelRole.CODING, confidence=0.85)

        # Reasoning
        if self._has(tl, ["why", "explain", "how does", "what is", "compare", "analyze", "suggest"]):
            return ClassifiedRequest(request=request, intent=Intent.REASONING, model_role=ModelRole.REASONING, confidence=0.8)

        # Chat
        if tl in ["hello", "hi", "hey", "how are you", "thanks", "bye"]:
            return ClassifiedRequest(request=request, intent=Intent.CHAT, model_role=ModelRole.CHAT, confidence=0.8)

        # Fallback
        return ClassifiedRequest(request=request, intent=Intent.REASONING, model_role=ModelRole.REASONING, confidence=0.5)
