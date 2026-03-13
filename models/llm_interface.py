"""
models/llm_interface.py — STRIX v3.0
=======================================
Multi-LLM pipeline:
  phi3       → fast chat / quick answers
  llama3.1   → reasoning / planning / complex questions
  qwen2.5-coder → all code tasks
"""

import os, sys, time, json, requests

# ── Load .env from E:\Strix\.env (root of project) ───────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))   # models/
_ROOT_DIR = os.path.dirname(_THIS_DIR)                   # E:\Strix\
_ENV_PATH = os.path.join(_ROOT_DIR, ".env")

try:
    from dotenv import load_dotenv
    if os.path.exists(_ENV_PATH):
        load_dotenv(_ENV_PATH, override=True)
        print(f"[LLM] Loaded .env from {_ENV_PATH}")
    else:
        load_dotenv()
        print(f"[LLM] .env not found at {_ENV_PATH} — using defaults")
except ImportError:
    pass

# Ensure brain/ and root are importable
for _p in (_ROOT_DIR, os.path.join(_ROOT_DIR, "brain")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── Model assignments ─────────────────────────────────────────
MODELS = {
    "chat":      os.getenv("CHAT_MODEL",      "phi3:latest"),
    "reasoning": os.getenv("REASONING_MODEL", "llama3.1:latest"),
    "coding":    os.getenv("CODING_MODEL",    "qwen2.5-coder:7b"),
    "frontend":  os.getenv("FRONTEND_MODEL",  "qwen2.5-coder:7b"),
    "backend":   os.getenv("BACKEND_MODEL",   "qwen2.5-coder:7b"),
    "planning":  os.getenv("PLANNING_MODEL",  "llama3.1:latest"),
}
print(f"[LLM] Models loaded: coding={MODELS['coding']} reasoning={MODELS['reasoning']}")

# Runtime overrides from GUI dropdown
_overrides = {}

_OPTIONS_CHAT = {
    "num_ctx":        2048,
    "num_predict":    512,
    "temperature":    0.7,
    "top_p":          0.9,
    "repeat_penalty": 1.1,
}

_OPTIONS_CODE = {
    "num_ctx":        4096,
    "num_predict":    2048,   # code needs more tokens
    "temperature":    0.2,    # lower temp = more deterministic code
    "top_p":          0.95,
    "repeat_penalty": 1.05,
}

_OPTIONS_REASON = {
    "num_ctx":        4096,
    "num_predict":    1024,
    "temperature":    0.5,
    "top_p":          0.9,
    "repeat_penalty": 1.1,
}


def get_model(key: str) -> str:
    """Get active model for a given role."""
    return _overrides.get(key) or MODELS.get(key, "phi3:latest")


def set_model_override(key: str, model: str):
    """Override a model role from the GUI."""
    _overrides[key] = model


def _trim_prompt(prompt: str, max_chars: int = 2000) -> str:
    if len(prompt) <= max_chars:
        return prompt
    return "...[trimmed]...\n" + prompt[-max_chars:]


def _call_ollama(model: str, prompt: str, system: str = "",
                 stream: bool = False, options: dict = None):
    """Core Ollama call — supports streaming and non-streaming."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model":   model,
        "prompt":  _trim_prompt(prompt),
        "system":  system,
        "stream":  stream,
        "options": options or _OPTIONS_CHAT,
    }
    try:
        if stream:
            return _stream_ollama(url, payload)
        r = requests.post(url, json=payload, timeout=60)
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
        with requests.post(url, json=payload, stream=True, timeout=60) as r:
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
    return _call_ollama(model, prompt, stream=stream, options=_OPTIONS_CHAT)


def call_reasoning_model(prompt: str, system: str = "", stream: bool = False):
    """llama3.1 — complex reasoning, planning, deep questions."""
    model = get_model("reasoning")
    print(f"[LLM] REASONING → {model}")
    return _call_ollama(model, prompt, system, stream=stream, options=_OPTIONS_REASON)


def call_coding_model(prompt: str, system: str = "", stream: bool = False):
    """qwen2.5-coder — Python, Java, C++, algorithms."""
    model = get_model("coding")
    print(f"[LLM] CODING → {model}")
    return _call_ollama(model, prompt, system, stream=stream, options=_OPTIONS_CODE)


def call_frontend_model(prompt: str, stream: bool = False):
    """qwen2.5-coder — HTML, CSS, React, UI code."""
    model = get_model("frontend")
    print(f"[LLM] FRONTEND → {model}")
    return _call_ollama(model, prompt, stream=stream, options=_OPTIONS_CODE)


def call_backend_model(prompt: str, stream: bool = False):
    """qwen2.5-coder — APIs, databases, server code."""
    model = get_model("backend")
    print(f"[LLM] BACKEND → {model}")
    return _call_ollama(model, prompt, stream=stream, options=_OPTIONS_CODE)


def call_planning_model(prompt: str, stream: bool = False):
    """llama3.1 — task decomposition and planning."""
    model = get_model("planning")
    print(f"[LLM] PLANNING → {model}")
    return _call_ollama(model, prompt, stream=stream, options=_OPTIONS_REASON)


# ── Backwards compat ──────────────────────────────────────────
def call_model_stream(model: str, prompt: str, system: str = ""):
    return _stream_ollama(
        f"{OLLAMA_BASE_URL}/api/generate",
        {"model": model, "prompt": _trim_prompt(prompt),
         "system": system, "stream": True, "options": _OPTIONS}
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