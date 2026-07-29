"""
Strix v5.0 Ollama Provider
Implements BaseModelProvider for the Ollama REST API.
"""
from __future__ import annotations

import json
import requests
import dataclasses
from typing import Optional, Iterator, Generator, Dict, Any, Union
from strix.types import ModelOptions
from strix.models.base import BaseModelProvider


class OllamaProvider(BaseModelProvider):
    def __init__(self, model_id: str, base_url: str = 'http://localhost:11434'):
        self._model_id = model_id
        self._base_url = base_url.rstrip('/')

    @property
    def name(self) -> str:
        return f"{self._model_id} via Ollama"

    @property
    def model_id(self) -> str:
        return self._model_id

    def _trim_prompt(self, prompt: str, max_chars: int = 6000) -> str:
        if len(prompt) > max_chars:
            return prompt[:max_chars] + "\n...[TRUNCATED]"
        return prompt

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m['name'] for m in data.get('models', [])]
                return self._model_id in models or f"{self._model_id}:latest" in models
            return False
        except requests.RequestException as e:
            print(f"[STRIX Ollama] Connection error during health check: {e}")
            return False

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = False,
        options: Optional[ModelOptions] = None
    ) -> Union[str, Iterator[str]]:
        mode = "streaming" if stream else "blocking"
        print(f"[STRIX Ollama] {self._model_id} generating ({mode})...")
        
        trimmed_prompt = self._trim_prompt(prompt)
        payload: Dict[str, Any] = {
            "model": self._model_id,
            "prompt": trimmed_prompt,
            "stream": stream
        }
        
        if system:
            payload["system"] = system
            
        if options:
            if dataclasses.is_dataclass(options):
                payload["options"] = dataclasses.asdict(options)
            else:
                payload["options"] = dict(options)

        url = f"{self._base_url}/api/generate"
        
        try:
            if stream:
                return self._stream_response(url, payload)
            else:
                resp = requests.post(url, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except requests.RequestException as e:
            print(f"[STRIX Ollama] Connection error during generate: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}")

    def _stream_response(self, url: str, payload: Dict[str, Any]) -> Generator[str, None, None]:
        try:
            with requests.post(url, json=payload, timeout=120, stream=True) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            continue
        except requests.RequestException as e:
            print(f"[STRIX Ollama] Connection error during streaming: {e}")
            raise RuntimeError(f"Ollama streaming failed: {e}")
