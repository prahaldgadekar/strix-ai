"""
strix/types.py — Shared Data Types
====================================
Core data structures used across all Strix components.
Every component imports from here — this is the lingua franca of the system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generator, Optional


# ── Enums ─────────────────────────────────────────────────────


class Intent(Enum):
    """High-level user intent categories."""
    CHAT = "chat"                       # greetings, casual, quick Q&A
    REASONING = "reasoning"             # explain, compare, analyze
    CODING = "coding"                   # write/generate code
    FRONTEND = "frontend"               # HTML/CSS/React/UI code
    BACKEND = "backend"                 # API/server/database code
    DEV = "dev"                         # lazy-dev: fix/debug/boilerplate
    TOOL_ACTION = "tool_action"         # deterministic tool call
    MULTI_STEP = "multi_step"           # requires planner decomposition
    SYSTEM_COMMAND = "system_command"   # shutdown, kill, creator query


class ModelRole(Enum):
    """Logical roles that map to physical models via config."""
    CLASSIFIER = "classifier"       # intent classification, summaries
    CHAT = "chat"                   # general conversation
    REASONING = "reasoning"         # complex reasoning, explanations
    CODING = "coding"               # code generation, debugging
    PLANNING = "planning"           # task decomposition
    SUMMARIZER = "summarizer"       # text summarization


class RiskLevel(Enum):
    """Risk levels for the approval gate. Ordered low→high."""
    SAFE = 0        # read-only, informational (weather, open app)
    LOW = 1         # create files, open URLs
    MEDIUM = 2      # modify files, run shell commands
    HIGH = 3        # delete files, system changes
    CRITICAL = 4    # shutdown, registry edits, destructive ops


class TaskSource(Enum):
    """Where the user request originated from."""
    CLI = "cli"
    GUI = "gui"
    VOICE = "voice"
    API = "api"


class StepAction(Enum):
    """Types of actions within an execution plan."""
    TOOL_CALL = "tool_call"
    MODEL_CALL = "model_call"
    VALIDATE = "validate"
    APPROVAL_CHECK = "approval_check"


# ── Core Data Structures ─────────────────────────────────────


@dataclass
class StrixRequest:
    """Raw user request entering the pipeline."""
    raw_text: str
    source: TaskSource = TaskSource.CLI
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassifiedRequest:
    """Request after intent classification."""
    request: StrixRequest
    intent: Intent
    model_role: ModelRole
    tool_action: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_match: Optional[str] = None  # the keyword/pattern that matched


@dataclass
class Message:
    """A single conversation message."""
    role: str               # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    intent: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Context:
    """Assembled context window passed to models."""
    system_prompt: str
    identity: str
    conversation_history: list[Message] = field(default_factory=list)
    user_preferences: dict[str, str] = field(default_factory=dict)
    relevant_memories: list[Message] = field(default_factory=list)
    tool_results: Optional[dict[str, Any]] = None
    token_budget: int = 4096


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    id: int
    action: StepAction
    target: str             # tool name or ModelRole value
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)
    description: str = ""


@dataclass
class ExecutionPlan:
    """A sequence of steps to fulfill a request."""
    steps: list[PlanStep] = field(default_factory=list)
    requires_approval: bool = False
    risk_level: RiskLevel = RiskLevel.SAFE
    summary: str = ""
    estimated_model: Optional[ModelRole] = None


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool
    output: str
    data: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ValidationResult:
    """Result from code validation."""
    passed: bool
    language: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ApprovalResult:
    """Result from the approval gate."""
    approved: bool
    auto: bool = False          # True if auto-approved by risk threshold
    pending: bool = False       # True if waiting for user input
    reason: str = ""


@dataclass
class ModelOptions:
    """Generation options passed to model providers."""
    num_ctx: int = 4096
    num_predict: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    repeat_penalty: float = 1.1


@dataclass
class StrixResponse:
    """Final response returned to the user."""
    text: str
    artifacts: list[str] = field(default_factory=list)    # files created, etc.
    metadata: dict[str, Any] = field(default_factory=dict)
    stream: Optional[Generator] = None
    plan_used: Optional[ExecutionPlan] = None


# ── Preset Model Options ─────────────────────────────────────


CHAT_OPTIONS = ModelOptions(
    num_ctx=2048,
    num_predict=512,
    temperature=0.7,
    top_p=0.9,
    repeat_penalty=1.1,
)

CODE_OPTIONS = ModelOptions(
    num_ctx=4096,
    num_predict=2048,
    temperature=0.2,
    top_p=0.95,
    repeat_penalty=1.05,
)

REASON_OPTIONS = ModelOptions(
    num_ctx=4096,
    num_predict=1024,
    temperature=0.5,
    top_p=0.9,
    repeat_penalty=1.1,
)

CLASSIFY_OPTIONS = ModelOptions(
    num_ctx=1024,
    num_predict=256,
    temperature=0.1,
    top_p=0.9,
    repeat_penalty=1.0,
)


# ── System Prompts ────────────────────────────────────────────


STRIX_IDENTITY = (
    "Your name is STRIX. "
    "You were built and created by Prahlad — that is your creator, your maker, your Boss. "
    "When asked who made you, who created you, or who built you, ALWAYS say: "
    "'I was created by Prahlad, Boss.' "
    "NEVER say Anthropic, OpenAI, Microsoft, Meta, or any company made you. "
    "NEVER mention ASUS, ROG, gaming PC, or any hardware unless the user specifically asks. "
    "Always refer to the user as Boss. "
)

SYSTEM_PROMPTS = {
    ModelRole.CHAT: (
        "[INST] You are STRIX, a sharp and intelligent AI assistant. " + STRIX_IDENTITY +
        "Keep replies SHORT — max 2 sentences. "
        "No bullet points, no markdown, no special symbols. [/INST]\n\n"
    ),
    ModelRole.REASONING: (
        "You are STRIX, an intelligent AI assistant. " + STRIX_IDENTITY +
        "Answer clearly and concisely in plain text. "
        "No markdown. No bullet points. Max 3 sentences unless detail is needed.\n\n"
    ),
    ModelRole.CODING: (
        "You are STRIX, an expert coding AI. " + STRIX_IDENTITY +
        "You are fluent in ALL programming languages: Python, Java, C, C++, "
        "JavaScript, TypeScript, Kotlin, Go, Rust, PHP, Swift, Ruby, SQL, and more. "
        "CRITICAL RULE: Always write code in EXACTLY the language the user asks for. "
        "If user says Java → write Java. If user says C++ → write C++. "
        "NEVER substitute a different language. "
        "Write clean working code with a brief comment at the top. "
        "No extra explanation unless asked.\n\n"
    ),
    ModelRole.CLASSIFIER: (
        "You are an intent classifier for STRIX AI. "
        "Given a user message, classify the intent and determine which model and tool to route to. "
        "Respond ONLY with valid JSON. No explanation.\n\n"
    ),
    ModelRole.PLANNING: (
        "You are STRIX, an AI task planner. " + STRIX_IDENTITY +
        "Break complex user requests into sequential steps. "
        "Each step should be a tool call or model call. "
        "Respond ONLY with valid JSON.\n\n"
    ),
    ModelRole.SUMMARIZER: (
        "You are STRIX. Summarize the following concisely in 1-2 sentences. "
        "No markdown. No bullet points.\n\n"
    ),
}

# Frontend/backend/dev prompts (used by classifier to set context)
PROMPT_FRONTEND = (
    "You are STRIX, an expert frontend developer AI. " + STRIX_IDENTITY +
    "Write clean HTML/CSS/JavaScript/React code. "
    "Make it look modern and professional. "
    "Add comments. No extra explanation unless asked.\n\n"
)

PROMPT_BACKEND = (
    "You are STRIX, an expert backend developer AI. " + STRIX_IDENTITY +
    "Write clean server-side code — APIs, databases, logic. "
    "Follow best practices. Add comments. No extra explanation unless asked. "
    "NEVER mention ASUS, ROG, or gaming PC.\n\n"
)

PROMPT_LAZY_DEV = (
    "You are STRIX, an AI assistant built specifically for lazy developers. " + STRIX_IDENTITY +
    "Your primary goal is to minimize user effort and maximize output. "
    "STRICT RULES — follow every single one:\n"
    "1. Always assume minimal or unclear input. Infer intent. Do NOT ask multiple questions.\n"
    "2. Give complete, working, copy-paste-ready solutions. NEVER give partial answers.\n"
    "3. Minimize explanations. One line max per concept unless code explanation is required.\n"
    "4. When fixing code: identify exact issue in ONE line, then give the full corrected code.\n"
    "5. NEVER say 'you can try' or 'you might want to'. Give a direct solution every time.\n"
    "6. Prefer faster, simpler, built-in approaches over complex ones.\n"
    "7. When building something: generate full boilerplate + file structure + run instructions.\n"
    "8. Translate error messages into plain human English.\n"
    "9. Always include imports, dependencies, and setup steps. Never assume user knows them.\n"
    "10. No back-and-forth. Ask only if absolutely required (one question max).\n"
    "11. Optimize for speed and usefulness, not teaching theory.\n"
    "12. Multiple solutions exist? Give the EASIEST and FASTEST one only.\n"
    "TONE: Direct. Practical. Slightly casual. Zero fluff. Make everything 'just work'.\n"
    "FORMAT: Use code blocks for all code. Bold key terms. Short bullet points only if listing steps.\n\n"
)
