"""
LLM-based classifier and ClassifierChain.
SLOW path — pure LLM call to classify intent.
"""
from __future__ import annotations
import json
from typing import Optional, Dict, Any

from strix.types import Intent, ModelRole, ClassifiedRequest, StrixRequest, Context, SYSTEM_PROMPTS
from strix.config import StrixConfig
from strix.classifier.base import BaseClassifier
from strix.classifier.rule_classifier import RuleClassifier

class LLMClassifier(BaseClassifier):
    def __init__(self, config: StrixConfig, model_registry):
        self.config = config
        self.model_registry = model_registry

    def classify(self, request: StrixRequest, context: Optional[Context] = None) -> ClassifiedRequest:
        raw_text = request.raw_text
        prompt = f"""
Analyze the following user request and classify its intent and appropriate model role.
Output ONLY a JSON object with this exact structure:
{{"intent": "coding", "model_role": "coding", "tool_action": null, "params": {{}}, "confidence": 0.9}}

Intents: SYSTEM_COMMAND, TOOL_ACTION, MULTI_STEP, FRONTEND, BACKEND, DEV, CODING, REASONING, CHAT
Roles: CLASSIFIER, CHAT, REASONING, CODING, PLANNING, SUMMARIZER

User Request: {raw_text}
"""
        try:
            provider = self.model_registry.get(ModelRole.CLASSIFIER) if self.model_registry else None
            if provider:
                response_str = provider.generate(prompt)
            else:
                response_str = ""

            text = response_str.strip() if isinstance(response_str, str) else ""
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()

            data = json.loads(text) if text else {}

            intent_str = str(data.get("intent", "REASONING")).lower()
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.CODING if any(w in raw_text.lower() for w in ["code", "python", "function", "write"]) else Intent.REASONING

            role_str = str(data.get("model_role", "reasoning")).lower()
            try:
                model_role = ModelRole(role_str)
            except ValueError:
                model_role = ModelRole.CODING if any(w in raw_text.lower() for w in ["code", "python", "function", "write"]) else ModelRole.REASONING

            tool_action = data.get("tool_action")
            params = data.get("params", {})
            confidence = float(data.get("confidence", 0.8))

            print(f"[STRIX LLMClassifier] Classified as {intent.value} (confidence={confidence})")

            return ClassifiedRequest(
                request=request,
                intent=intent,
                model_role=model_role,
                confidence=confidence,
                tool_action=tool_action,
                params=params
            )
        except Exception as e:
            print(f"[STRIX LLMClassifier] Error classifying: {e}")
            is_code = any(w in raw_text.lower() for w in ["code", "python", "function", "write", "add"])
            return ClassifiedRequest(
                request=request,
                intent=Intent.CODING if is_code else Intent.REASONING,
                model_role=ModelRole.CODING if is_code else ModelRole.REASONING,
                confidence=0.5
            )


class ClassifierChain:
    def __init__(self, rule_classifier: RuleClassifier, llm_classifier: LLMClassifier, threshold: float = 0.7):
        self.rule_classifier = rule_classifier
        self.llm_classifier = llm_classifier
        self.threshold = threshold

    def classify(self, request: StrixRequest, context: Optional[Context] = None) -> ClassifiedRequest:
        result = self.rule_classifier.classify(request, context)
        print(f"[STRIX ClassifierChain] Rule confidence={result.confidence}, using {'rule' if result.confidence >= self.threshold else 'llm'} path")
        
        if result.confidence >= self.threshold:
            return result
            
        return self.llm_classifier.classify(request, context)
