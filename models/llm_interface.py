"""
models/llm_interface.py — STRIX v4.1
=======================================
UPGRADE: Every task type gets its own LLM model assignment.
Each model is chosen for speed vs intelligence tradeoff:

  phi3         → FAST: chat, greetings, quick answers, music commands,
                        system queries, direct tool calls
  llama3.1     → SMART: reasoning, planning, complex questions,
                          analysis, explanations
  qwen2.5-coder → CODE: all code tasks (Python, Java, C++, web, etc.)

Task-to-model mapping:
  chat       → phi3          (fast 2-sentence replies)
  music      → phi3          (just parse song name, no thinking needed)
  quick      → phi3          (system status, jokes, ip, weather response)
  coding     → qwen2.5-coder (any programming language)
  frontend   → qwen2.5-coder (HTML/CSS/React)
  backend    → qwen2.5-coder (APIs, databases)
  reasoning  → llama3.1      (explain, compare, advise)
  planning   → llama3.1      (multi-step task decomposition)
  search     → phi3          (format search results)
"""

import os, time, json, requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── Model assignments — override from .env or GUI ─────────────
MODELS = {
    # Fast tasks (phi3)
    "chat":     os.getenv("CHAT_MODEL",     "phi3:latest"),
    "music":    os.getenv("MUSIC_MODEL",    "phi3:latest"),   # NEW
    "quick":    os.getenv("QUICK_MODEL",    "phi3:latest"),   # NEW
    "search":   os.getenv("SEARCH_MODEL",   "phi3:latest"),   # NEW

    # Code tasks (qwen2.5-coder)
    "coding":   os.getenv("CODING_MODEL",   "qwen2.5-coder:latest"),
    "frontend": os.getenv("FRONTEND_MODEL", "qwen2.5-coder:latest"),
    "backend":  os.getenv("BACKEND_MODEL",  "qwen2.5-coder:latest"),

    # Complex tasks (llama3.1)
    "reasoning":os.getenv("REASONING_MODEL","llama3.1:latest"),
    "planning": os.getenv("PLANNING_MODEL", "llama3.1:latest"),
}

# Runtime overrides from GUI dropdown
_overrides = {}

# Generation options — tuned per model type
_OPTIONS_FAST = {
    "num_ctx":        1024,   # smaller context = faster for phi3
    "num_predict":    256,    # short replies for chat/quick tasks
    "temperature":    0.6,
    "top_p":          0.9,
    "repeat_penalty": 1.1,
}

_OPTIONS_CODE = {
    "num_ctx":        4096,   # larger context for code tasks
    "num_predict":    1024,
    "temperature":    0.2,    # low temp = precise code
    "top_p":          0.95,
    "repeat_penalty": 1.1,
}

_OPTIONS_REASON = {
    "num_ctx":        2048,
    "num_predict":    512,
    "temperature":    0.7,
    "top_p":          0.9,
    "repeat_penalty": 1.1,
}

# Map model role → options
_ROLE_OPTIONS = {
    "chat":     _OPTIONS_FAST,
    "music":    _OPTIONS_FAST,
    "quick":    _OPTIONS_FAST,
    "search":   _OPTIONS_FAST,
    "coding":   _OPTIONS_CODE,
    "frontend": _OPTIONS_CODE,
    "backend":  _OPTIONS_CODE,
    "reasoning":_OPTIONS_REASON,
    "planning": _OPTIONS_REASON,
}


def get_model(key: str) -> str:
    """Get active model for a given role."""
    return _overrides.get(key) or MODELS.get(key, "phi3:latest")


def set_model_override(key: str, model: str):
    """Override a model role from the GUI."""
    _overrides[key] = model


def get_model_options(key: str) -> dict:
    """Get generation options for a role."""
    return _ROLE_OPTIONS.get(key, _OPTIONS_REASON)


def _trim_prompt(prompt: str, max_chars: int = 3000) -> str:
    if len(prompt) <= max_chars:
        return prompt
    return "...[trimmed]...\n" + prompt[-max_chars:]


def _call_ollama(model: str, prompt: str, system: str = "",
                 stream: bool = False, role: str = "reasoning"):
    """Core Ollama call — supports streaming and non-streaming."""
    url     = f"{OLLAMA_BASE_URL}/api/generate"
    options = get_model_options(role)
    payload = {
        "model":   model,
        "prompt":  _trim_prompt(prompt),
        "system":  system,
        "stream":  stream,
        "options": options,
    }
    try:
        if stream:
            return _stream_ollama(url, payload)
        r = requests.post(url, json=payload, timeout=90)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        err = "ERROR: Ollama not running. Start with: ollama serve"
        return iter([err]) if stream else err
    except requests.exceptions.Timeout:
        err = "ERROR: Model timed out. Try phi3 for faster responses."
        return iter([err]) if stream else err
    except Exception as e:
        err = f"ERROR: {e}"
        return iter([err]) if stream else err


def _stream_ollama(url: str, payload: dict):
    """Generator that yields tokens one by one."""
    try:
        with requests.post(url, json=payload, stream=True, timeout=90) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    try:
                        data  = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        yield f"\n[Stream error: {e}]"


# ── Public model callers ──────────────────────────────────────

def call_chat_model(prompt: str, stream: bool = False):
    """phi3 — fast replies, greetings, quick questions."""
    model = get_model("chat")
    print(f"[LLM] CHAT → {model}")
    return _call_ollama(model, prompt, stream=stream, role="chat")


def call_music_model(prompt: str, stream: bool = False):
    """phi3 — parse music commands, song names. Fast."""
    model = get_model("music")
    print(f"[LLM] MUSIC → {model}")
    return _call_ollama(model, prompt, stream=stream, role="music")


def call_quick_model(prompt: str, stream: bool = False):
    """phi3 — quick tool result formatting (weather, system, jokes)."""
    model = get_model("quick")
    print(f"[LLM] QUICK → {model}")
    return _call_ollama(model, prompt, stream=stream, role="quick")


def call_reasoning_model(prompt: str, system: str = "", stream: bool = False):
    """llama3.1 — complex reasoning, analysis, deep questions."""
    model = get_model("reasoning")
    print(f"[LLM] REASONING → {model}")
    return _call_ollama(model, prompt, system, stream=stream, role="reasoning")


def call_coding_model(prompt: str, system: str = "", stream: bool = False):
    """qwen2.5-coder — Python, Java, C++, algorithms."""
    model = get_model("coding")
    print(f"[LLM] CODING → {model}")
    return _call_ollama(model, prompt, system, stream=stream, role="coding")


def call_frontend_model(prompt: str, stream: bool = False):
    """qwen2.5-coder — HTML, CSS, React, UI code."""
    model = get_model("frontend")
    print(f"[LLM] FRONTEND → {model}")
    return _call_ollama(model, prompt, stream=stream, role="frontend")


def call_backend_model(prompt: str, stream: bool = False):
    """qwen2.5-coder — APIs, databases, server code."""
    model = get_model("backend")
    print(f"[LLM] BACKEND → {model}")
    return _call_ollama(model, prompt, stream=stream, role="backend")


def call_planning_model(prompt: str, stream: bool = False):
    """llama3.1 — task decomposition and planning."""
    model = get_model("planning")
    print(f"[LLM] PLANNING → {model}")
    return _call_ollama(model, prompt, stream=stream, role="planning")


# ── Backwards compat ──────────────────────────────────────────
def call_model_stream(model: str, prompt: str, system: str = ""):
    return _stream_ollama(
        f"{OLLAMA_BASE_URL}/api/generate",
        {"model": model, "prompt": _trim_prompt(prompt),
         "system": system, "stream": True, "options": _OPTIONS_REASON}
    )


def set_models(reasoning: str = None, coding: str = None):
    if reasoning: _overrides["reasoning"] = reasoning
    if coding:    _overrides["coding"]    = coding


def is_ollama_running(retries: int = 3, wait: float = 2.0) -> bool:
    for i in range(retries):
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=4)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        if i < retries - 1:
            time.sleep(wait)
    return False


def list_available_models() -> list:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []