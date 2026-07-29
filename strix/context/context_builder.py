from __future__ import annotations
from strix.types import (ClassifiedRequest, Context, Intent, ModelRole,
                          SYSTEM_PROMPTS, STRIX_IDENTITY, PROMPT_FRONTEND,
                          PROMPT_BACKEND, PROMPT_LAZY_DEV)
from strix.config import StrixConfig

class ContextBuilder:
    """Assembles context for Strix requests."""
    
    def __init__(self, conversation_memory, persistent_memory, preferences_store, config: StrixConfig):
        self.conversation_memory = conversation_memory
        self.persistent_memory = persistent_memory
        self.preferences_store = preferences_store
        self.config = config
        print("[STRIX ContextBuilder] Initialized")
        
    def get_prompt_for_intent(self, intent: Intent) -> str:
        """Returns appropriate system prompt based on intent."""
        if intent == Intent.FRONTEND:
            return PROMPT_FRONTEND
        elif intent == Intent.BACKEND:
            return PROMPT_BACKEND
        elif intent == Intent.DEV:
            return PROMPT_LAZY_DEV
        elif hasattr(intent, 'name') and intent.name in SYSTEM_PROMPTS:
            return SYSTEM_PROMPTS[intent.name]
        else:
            return STRIX_IDENTITY

    def build(self, request: ClassifiedRequest) -> Context:
        """Assembles context from various memory sources and system prompts."""
        print(f"[STRIX ContextBuilder] Building context for intent: {request.intent.name}")
        system_prompt = self.get_prompt_for_intent(request.intent)
        
        recent_history = []
        if self.conversation_memory:
            recent_history = self.conversation_memory.get_recent()
            
        preferences = {}
        if self.preferences_store:
            preferences = self.preferences_store.get_all()
            
        relevant_memories = []
        if self.persistent_memory and request.intent not in [Intent.TOOL_ACTION, Intent.SYSTEM_COMMAND, Intent.MULTI_STEP]:
            relevant_memories = self.persistent_memory.search(request.request.raw_text)
            
        return Context(
            system_prompt=system_prompt,
            identity=STRIX_IDENTITY,
            conversation_history=recent_history,
            user_preferences=preferences,
            relevant_memories=relevant_memories,
            token_budget=self.config.max_context_tokens if self.config else 4096
        )
