from __future__ import annotations
from strix.config import StrixConfig
from strix.types import (StrixRequest, StrixResponse, TaskSource, Intent)
from strix.memory.conversation import ConversationMemory
from strix.memory.persistent import PersistentMemory
from strix.memory.preferences import PreferencesStore
from strix.models.registry import ModelRegistry
from strix.tools.registry import ToolRegistry
from strix.classifier.rule_classifier import RuleClassifier
from strix.classifier.llm_classifier import LLMClassifier, ClassifierChain
from strix.context.context_builder import ContextBuilder
from strix.planner.direct_planner import DirectPlanner
from strix.planner.llm_planner import LLMPlanner, PlannerChain
from strix.approval.approval_gate import ApprovalGate
from strix.orchestrator.orchestrator import Orchestrator
from strix.response.response_generator import ResponseGenerator

class StrixPipeline:
    """Main processing pipeline for Strix v5.0 requests."""
    
    def __init__(self, config: StrixConfig = None):
        self.config = config or StrixConfig.load()
        
        self.persistent_memory = PersistentMemory(self.config.memory_db_path)
        self.conversation_memory = ConversationMemory(max_messages=50)
        self.preferences_store = PreferencesStore(self.config.memory_db_path)
        
        self.model_registry = ModelRegistry(self.config)
        self.tool_registry = ToolRegistry()
        if hasattr(self.tool_registry, 'register_defaults'):
            self.tool_registry.register_defaults(self.config)
            
        self.rule_classifier = RuleClassifier(self.config)
        self.llm_classifier = LLMClassifier(self.config, self.model_registry)
        self.classifier_chain = ClassifierChain(self.rule_classifier, self.llm_classifier)
        
        self.context_builder = ContextBuilder(
            self.conversation_memory, 
            self.persistent_memory, 
            self.preferences_store, 
            self.config
        )
        self.direct_planner = DirectPlanner(self.config)
        self.llm_planner = LLMPlanner(self.config, self.model_registry)
        self.planner_chain = PlannerChain(self.direct_planner, self.llm_planner)

        self.approval_gate = ApprovalGate(self.config)
        self.orchestrator = Orchestrator(self.model_registry, self.tool_registry, self.config)
        self.response_generator = ResponseGenerator(self.conversation_memory, self.persistent_memory)
        
        print(f"[STRIX Pipeline] Initialized with models: "
              f"classifier={self.config.classifier_model}, "
              f"chat={self.config.chat_model}, "
              f"reasoning={self.config.reasoning_model}, "
              f"coding={self.config.coding_model}")
              
    def process(self, raw_text: str, source: str = 'cli', stream: bool = False, approval_callback=None) -> StrixResponse:
        try:
            task_source = TaskSource(source)
        except ValueError:
            task_source = TaskSource.CLI
        request = StrixRequest(raw_text=raw_text, source=task_source)
        self.conversation_memory.save("user", raw_text)
        self.persistent_memory.save("user", raw_text, session_id=request.session_id)
        
        classified = self.classifier_chain.classify(request)
        context = self.context_builder.build(classified)
        plan = self.planner_chain.plan(classified, context)
        
        if not plan:
            return StrixResponse(text="Error: Could not generate a plan for the request.")
            
        if plan.requires_approval:
            approval = self.approval_gate.check(plan, approval_callback)
            if not approval.approved:
                return StrixResponse(text=f"Execution cancelled: {approval.reason}")
                
        response = self.orchestrator.execute(plan, context, stream=stream)
        
        if response.text in ['STRIX_SHUTDOWN', 'STRIX_KILL'] or (response.text and response.text.startswith("I am Strix")):
            return response
            
        if not (stream and response.stream):
            response = self.response_generator.format(response)
            self.response_generator.save_to_memory(response)
            
        return response
        
    def get_history(self, limit: int = 200) -> list[dict[str, str]]:
        if hasattr(self, 'conversation_memory') and self.conversation_memory:
            msgs = self.conversation_memory.get_recent(limit=limit)
            return [{"role": m.role, "content": m.content} for m in msgs]
        return []

    def get_model_registry(self) -> ModelRegistry:
        return self.model_registry

    def get_tool_registry(self) -> ToolRegistry:
        return self.tool_registry

    def clear_memory(self):
        if hasattr(self, 'conversation_memory') and self.conversation_memory:
            with self.conversation_memory._lock:
                self.conversation_memory._messages.clear()

class StrixBrainCompat:
    """Backward-compatible wrapper matching the old StrixBrain interface."""
    def __init__(self):
        self._pipeline = StrixPipeline()
        print('[STRIX Brain] Ready.')
        print(f'[STRIX] v5.0 Pipeline initialized')
    
    def process(self, raw: str, stream: bool = False):
        response = self._pipeline.process(raw, source='cli', stream=stream)
        if stream and response.stream:
            return response.stream
        return response.text

    def get_history(self, limit: int = 200):
        return self._pipeline.get_history(limit=limit)

    def clear_memory(self):
        self._pipeline.clear_memory()
