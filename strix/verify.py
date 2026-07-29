"""Strix v5.0 - Full Integration Verification (Phase 1 & 2)"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 55)
print("  STRIX v5.0 - Full Integration Verification (Phase 1 & 2)")
print("=" * 55)
print()

# 1. Pipeline Init
print("1. Pipeline Initialization...")
from strix.pipeline import StrixPipeline
p = StrixPipeline()
print("   [OK] Pipeline initialized successfully")
print()

# 2. Classifier Tests
print("2. Classifier Routing Tests:")
from strix.classifier.rule_classifier import RuleClassifier
from strix.config import StrixConfig
from strix.types import StrixRequest

c = RuleClassifier(StrixConfig.load())
tests = [
    ("hello",                   "chat",           None),
    ("open chrome",             "tool_action",    "open_app"),
    ("what is the weather",     "tool_action",    "get_weather"),
    ("explain recursion",       "reasoning",      None),
    ("who made you",            "system_command", None),
    ("play eminem",             "tool_action",    "play_spotify"),
    ("write a python function", "coding",         None),
    ("fix this bug",            "dev",            None),
    ("shutdown",                "system_command", None),
    ("open youtube",            "tool_action",    "open_url"),
    ("tell me a joke",          "tool_action",    "get_joke"),
    ("what is my ip",           "tool_action",    "get_ip_info"),
]

passed = 0
failed = 0
for text, expected_intent, expected_tool in tests:
    r = c.classify(StrixRequest(text))
    intent_ok = r.intent.value == expected_intent
    tool_ok = expected_tool is None or r.tool_action == expected_tool
    ok = intent_ok and tool_ok
    status = "OK" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    tool_str = f"tool={r.tool_action}" if r.tool_action else f"model={r.model_role.value}"
    print(f"   [{status:4s}] {text:30s} -> {r.intent.value:15s} {tool_str}")

print(f"\n   Results: {passed}/{passed+failed} passed")
print()

# 3. Creator Response
print("3. Creator Response (via full pipeline):")
r = p.process("who made you")
print(f"   -> {r.text}")
print()

# 4. Tool Registry (36 tools)
print("4. Tool Registry:")
tr = p.get_tool_registry()
tools = tr.list_all()
print(f"   {len(tools)} tools registered (including run_oi_task)")
has_oi = tr.get("run_oi_task") is not None
print(f"   [OK] OpenInterpreterTool registered: {has_oi}")
print()

# 5. Model Registry
print("5. Model Registry:")
mr = p.get_model_registry()
for role, model in mr.get_all().items():
    print(f"   {role:12s} -> {model}")
print()

# 6. Speech Subsystem
print("6. Speech Subsystem:")
from strix.speech import SpeechTTS, SpeechRecognizer
tts = SpeechTTS()
rec = SpeechRecognizer()
print(f"   [OK] SpeechTTS initialized (available={tts.is_available})")
print(f"   [OK] SpeechRecognizer initialized (available={rec.is_available})")
print()

# 7. Planner System (PlannerChain & LLMPlanner)
print("7. Planning Subsystem:")
from strix.planner import PlannerChain, DirectPlanner, LLMPlanner
dp = DirectPlanner(StrixConfig.load())
lp = LLMPlanner(StrixConfig.load(), p.get_model_registry())
pc = PlannerChain(dp, lp)
print("   [OK] PlannerChain & LLMPlanner initialized successfully")
print()

# 8. Backward Compat
print("8. Backward Compatibility (StrixBrainCompat):")
from strix.pipeline import StrixBrainCompat
brain = StrixBrainCompat()
result = brain.process("who made you")
print(f"   -> {result}")
print()

print("=" * 55)
if failed == 0 and has_oi:
    print("  ALL TESTS PASSED")
else:
    print(f"  {failed} TEST(S) FAILED")
print("=" * 55)
