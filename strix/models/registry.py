"""
Strix v5.0 Model Registry
Maps ModelRole enums to BaseModelProvider instances.
"""
from __future__ import annotations

import requests
from typing import Dict, List, Optional
from strix.types import ModelRole
from strix.config import StrixConfig
from strix.models.base import BaseModelProvider
from strix.models.ollama_provider import OllamaProvider


class ModelRegistry:
    def __init__(self, config: StrixConfig):
        self._providers: Dict[ModelRole, BaseModelProvider] = {}
        
        print("[STRIX ModelRegistry] Initializing registry...")
        
        # Map each ModelRole to its configured model from StrixConfig
        base_url = config.ollama_base_url
        default_roles = [
            (ModelRole.CLASSIFIER,  config.classifier_model),
            (ModelRole.CHAT,        config.chat_model),
            (ModelRole.REASONING,   config.reasoning_model),
            (ModelRole.CODING,      config.coding_model),
            (ModelRole.PLANNING,    config.planning_model),
            (ModelRole.SUMMARIZER,  config.summarizer_model),
        ]

        for role, model_id in default_roles:
            self.register(role, OllamaProvider(model_id, base_url=base_url))

        print(f"[STRIX ModelRegistry] Registered {len(default_roles)} model roles")

    def get(self, role: ModelRole) -> BaseModelProvider:
        provider = self._providers.get(role)
        if provider and provider.is_available():
            print(f"[STRIX ModelRegistry] Using {getattr(provider, 'model_id', 'unknown')} for {role}")
            return provider
            
        # Fallback 1: Try CHAT model
        chat_provider = self._providers.get(ModelRole.CHAT)
        if chat_provider and chat_provider.is_available():
            print(f"[STRIX ModelRegistry] Using {getattr(chat_provider, 'model_id', 'unknown')} (fallback) for {role}")
            return chat_provider
            
        # Fallback 2: Any available model
        for r, p in self._providers.items():
            if p.is_available():
                print(f"[STRIX ModelRegistry] Using {getattr(p, 'model_id', 'unknown')} (fallback any) for {role}")
                return p
                
        raise RuntimeError(f"No available providers found for role {role} and no fallbacks available.")

    def register(self, role: ModelRole, provider: BaseModelProvider) -> None:
        self._providers[role] = provider

    def override(self, role: ModelRole, model_id: str) -> None:
        self.register(role, OllamaProvider(model_id))

    @staticmethod
    def list_available() -> List[str]:
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m['name'] for m in data.get('models', [])]
        except Exception as e:
            print(f"[STRIX ModelRegistry] Error listing available models: {e}")
            return []

    def get_all(self) -> Dict[str, str]:
        result = {}
        for role, provider in self._providers.items():
            if hasattr(provider, 'model_id'):
                result[role.name] = provider.model_id
            else:
                result[role.name] = "unknown"
        return result
