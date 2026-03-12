"""
brain/router.py — STRIX v4.1
==============================
UPGRADE: New task-specific model routing.

Every task type now has the RIGHT model assigned:
  phi3         → chat, music, quick, search  (fast, small)
  llama3.1     → reasoning, planning          (smart, complex)
  qwen2.5-coder → coding, frontend, backend  (precise code)

New model keys added:
  "music"  → phi3  — parse song commands, music control replies
  "quick"  → phi3  — system status, jokes, weather summary
  "search" → phi3  — format search results
"""

import time
from models.llm_interface import (
    call_chat_model, call_reasoning_model, call_coding_model,
    call_frontend_model, call_backend_model, call_planning_model,
    call_music_model, call_quick_model,
    is_ollama_running, _call_ollama
)

# ── Identity block ────────────────────────────────────────────
_IDENTITY = (
    "Your name is STRIX. "
    "You were built and created by Prahlad — that is your creator, your maker, your Boss. "
    "When asked who made you, who created you, or who built you, ALWAYS say: "
    "'I was created by Prahlad, Boss.' "
    "NEVER say Anthropic, OpenAI, Microsoft, Meta, or any company made you. "
    "NEVER mention ASUS, ROG, gaming PC, or any hardware unless the user specifically asks. "
    "Always refer to the user as Boss. "
)

# ── System prompts per role ───────────────────────────────────
PROMPT_CHAT = (
    "[INST] You are STRIX, a sharp and intelligent AI assistant. " + _IDENTITY +
    "Keep replies SHORT — max 2 sentences. "
    "No bullet points, no markdown, no special symbols. [/INST]\n\n"
)

PROMPT_MUSIC = (
    "[INST] You are STRIX, a music assistant. " + _IDENTITY +
    "Confirm music commands in ONE short sentence. "
    "Example: 'Playing co2, Boss.' or 'Paused, Boss.' "
    "No explanation needed. [/INST]\n\n"
)

PROMPT_QUICK = (
    "[INST] You are STRIX, an efficient assistant. " + _IDENTITY +
    "Give ONE short, direct answer. Max 1 sentence. No padding. [/INST]\n\n"
)

PROMPT_REASON = (
    "You are STRIX, an intelligent AI assistant. " + _IDENTITY +
    "Answer clearly and concisely in plain text. "
    "No markdown. No bullet points. Max 3 sentences unless detail is needed.\n\n"
)

PROMPT_CODE = (
    "You are STRIX, an expert coding AI. " + _IDENTITY +
    "You are fluent in ALL programming languages: Python, Java, C, C++, "
    "JavaScript, TypeScript, Kotlin, Go, Rust, PHP, Swift, Ruby, SQL, and more. "
    "CRITICAL RULE: Always write code in EXACTLY the language the user asks for. "
    "If user says Java → write Java. If user says C++ → write C++. "
    "NEVER substitute a different language. "
    "Write clean working code with a brief comment at the top. "
    "No extra explanation unless asked.\n\n"
)

PROMPT_FRONTEND = (
    "You are STRIX, an expert frontend developer AI. " + _IDENTITY +
    "Write clean HTML/CSS/JavaScript/React code. "
    "Make it look modern and professional. "
    "Add comments. No extra explanation unless asked.\n\n"
)

PROMPT_BACKEND = (
    "You are STRIX, an expert backend developer AI. " + _IDENTITY +
    "Write clean server-side code — APIs, databases, logic. "
    "Follow best practices. Add comments. No extra explanation unless asked.\n\n"
)

TOOL_ACTIONS = {
    "get_weather", "get_news", "get_system_status",
    "search_file", "read_file", "directory_tree",
    "create_java_project", "create_c_project", "create_cpp_project",
    "create_python_project", "list_projects",
    "remember_preference", "get_preferences",
    "create_desktop_file", "create_desktop_folder",
    "list_desktop", "delete_desktop_file", "open_app", "open_explorer",
    "get_crypto", "get_top_crypto", "get_joke",
    "get_nasa", "get_ip_info", "get_exchange",
    "wiki_search", "get_github",
    "create_file_in_folder",
    "play_spotify", "play_playlist", "search_files", "open_url",
    "create_code_file", "oi_task",
    "music_pause", "music_resume", "music_next", "music_prev", "music_stop",
}


# ── Language detector ────────────────────────────────────────
_LANG_KEYWORDS = {
    "java": "Java", "kotlin": "Kotlin",
    "c++": "C++", "cpp": "C++", "c#": "C#", "csharp": "C#",
    "javascript": "JavaScript", "typescript": "TypeScript",
    "nodejs": "JavaScript (Node.js)", " node ": "JavaScript (Node.js)",
    "golang": "Go", " go ": "Go", "rust": "Rust", "php": "PHP",
    "swift": "Swift", "ruby": "Ruby", "scala": "Scala",
    "dart": "Dart", "flutter": "Dart (Flutter)", "perl": "Perl",
    "matlab": "MATLAB", " sql": "SQL", "bash": "Bash", "shell": "Shell/Bash",
    ".java": "Java", ".js": "JavaScript", ".ts": "TypeScript",
    ".kt": "Kotlin", ".cpp": "C++", ".cs": "C#", ".go": "Go",
    ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    "python": "Python", ".py": "Python",
}

def _detect_language(prompt: str) -> str:
    tl = " " + prompt.lower() + " "
    for kw, lang in _LANG_KEYWORDS.items():
        if kw in tl:
            return lang
    return ""


def route_task(task: dict, stream: bool = False):
    action = task.get("action", "llm_response")
    params = task.get("params", {})

    if action in TOOL_ACTIONS:
        return _run_tool(action, params)

    if action == "llm_response":
        prompt    = params.get("prompt", task.get("description", ""))
        model_key = params.get("model", "chat")
        return _route_to_model(prompt, model_key, stream=stream)

    return _route_to_model(task.get("description", ""), "chat", stream=stream)


def _route_to_model(prompt: str, model_key: str, stream: bool = False):
    """
    Route prompt to correct model based on task type.

    chat      → phi3        (fast 2-sentence replies)
    music     → phi3        (song command confirmations)
    quick     → phi3        (short direct answers)
    reasoning → llama3.1    (explain, compare, analyse)
    planning  → llama3.1    (multi-step planning)
    coding    → qwen2.5-coder
    frontend  → qwen2.5-coder
    backend   → qwen2.5-coder
    """
    # Wait for Ollama
    for attempt in range(5):
        if is_ollama_running(retries=1, wait=0):
            break
        wait = 3 if attempt < 3 else 6
        print(f"[Router] Waiting for Ollama {wait}s (try {attempt+1}/5)...")
        time.sleep(wait)
    else:
        msg = "STRIX offline. Please start Ollama with: ollama serve"
        return iter([msg]) if stream else msg

    if model_key == "chat":
        return call_chat_model(PROMPT_CHAT + prompt, stream=stream)

    elif model_key == "music":
        return call_music_model(PROMPT_MUSIC + prompt, stream=stream)

    elif model_key == "quick":
        return call_quick_model(PROMPT_QUICK + prompt, stream=stream)

    elif model_key == "reasoning":
        return call_reasoning_model(PROMPT_REASON + prompt, stream=stream)

    elif model_key == "coding":
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this code in {lang} ONLY.\n" if lang else ""
        return call_coding_model(PROMPT_CODE + lang_note + prompt, stream=stream)

    elif model_key == "frontend":
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this in {lang} ONLY.\n" if lang else ""
        return call_frontend_model(PROMPT_FRONTEND + lang_note + prompt, stream=stream)

    elif model_key == "backend":
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this in {lang} ONLY.\n" if lang else ""
        return call_backend_model(PROMPT_BACKEND + lang_note + prompt, stream=stream)

    elif model_key == "planning":
        return call_planning_model(PROMPT_REASON + prompt, stream=stream)

    elif model_key in ("qwen2.5-coder", "qwen2.5-coder:latest"):
        # Direct model name used by code-in-chat path
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this code in {lang} ONLY.\n" if lang else ""
        return call_coding_model(PROMPT_CODE + lang_note + prompt, stream=stream)

    else:
        # Fallback → chat
        return call_chat_model(PROMPT_CHAT + prompt, stream=stream)


def _run_tool(action: str, params: dict) -> str:

    if action == "get_weather":
        from api.weather import format_weather
        return format_weather(params.get("city"))

    if action == "get_news":
        from api.news import format_news
        return format_news(params.get("category", "technology"), params.get("count", 5))

    if action == "get_system_status":
        from tools.system_tools import get_system_summary
        return get_system_summary()

    if action == "wiki_search":
        from api.extras import search_wikipedia
        return search_wikipedia(params.get("query", ""))

    if action == "get_crypto":
        from api.extras import get_crypto_price
        return get_crypto_price(params.get("coin", "bitcoin"))

    if action == "get_top_crypto":
        from api.extras import get_top_crypto
        return get_top_crypto()

    if action == "get_joke":
        try:
            import pyjokes
            joke = pyjokes.get_joke(language="en", category="neutral")
            return f"Here is one for you Boss — {joke}"
        except ImportError:
            from api.extras import get_joke
            return get_joke()

    if action == "get_nasa":
        from api.extras import get_nasa_apod
        return get_nasa_apod()

    if action == "get_ip_info":
        from api.extras import get_my_ip_info
        return get_my_ip_info()

    if action == "get_exchange":
        from api.extras import get_exchange_rate
        return get_exchange_rate(params.get("from", "USD"), params.get("to", "INR"))

    if action == "get_github":
        from api.extras import get_github_profile
        username = params.get("username", "")
        if not username:
            return "Please tell me the GitHub username Boss."
        return get_github_profile(username)

    if action == "search_file":
        from tools.search_tools import search_files, format_search_results
        return format_search_results(search_files(params.get("query", "")))

    if action == "read_file":
        from tools.search_tools import read_file
        return read_file(params.get("path", ""))

    if action == "directory_tree":
        from tools.search_tools import get_directory_tree
        return get_directory_tree(params.get("path", "."))

    if action == "create_java_project":
        from tools.project_tools import create_java_project
        return create_java_project(params.get("name", "MyProject"))

    if action == "create_c_project":
        from tools.project_tools import create_c_project
        return create_c_project(params.get("name", "MyProject"))

    if action == "create_cpp_project":
        from tools.project_tools import create_cpp_project
        return create_cpp_project(params.get("name", "MyProject"))

    if action == "create_python_project":
        from tools.project_tools import create_python_project
        return create_python_project(params.get("name", "MyProject"))

    if action == "list_projects":
        from tools.project_tools import list_projects
        return list_projects()

    if action == "remember_preference":
        from memory.memory_db import set_preference
        key = params.get("key", "")
        val = params.get("value", "")
        if key:
            set_preference(key, val)
            return "Got it Boss, I will remember that."
        return "No key provided."

    if action == "get_preferences":
        from memory.memory_db import get_all_preferences
        prefs = get_all_preferences()
        if not prefs:
            return "No preferences saved yet."
        return "Your preferences: " + ", ".join(f"{k} is {v}" for k, v in prefs.items())

    if action == "create_desktop_file":
        from tools.windows_tools import create_file_on_desktop
        return create_file_on_desktop(params.get("filename", "file.txt"), params.get("content", ""))

    if action == "create_desktop_folder":
        from tools.windows_tools import create_folder_on_desktop
        return create_folder_on_desktop(params.get("foldername", "NewFolder"))

    if action == "list_desktop":
        from tools.windows_tools import list_desktop_files
        return list_desktop_files()

    if action == "search_files":
        from tools.windows_tools import search_files
        return search_files(
            query       = params.get("query", ""),
            search_path = params.get("search_path", None)
        )

    if action == "open_url":
        import subprocess, os
        url     = params.get("url", "")
        profile = params.get("profile", "main")
        if not url:
            return "No URL provided."

        uname = os.environ.get("USERNAME", "")
        local = os.environ.get("LOCALAPPDATA") or os.path.join("C:\\Users", uname, "AppData", "Local")

        dev_chrome = os.path.join(local, "Google", "Chrome Dev", "Application", "chrome.exe")
        default_chrome_paths = [
            os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", "C:/Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        default_chrome = next((p for p in default_chrome_paths if os.path.exists(p)), None)

        # ═══════════════════════════════════════════════════════
        # Chrome routing:
        #   profile="work" → prahaldgadekar64@gmail.com   → Default Chrome
        #   profile="main" → prahladgadekar1569@gmail.com → Dev Chrome
        # ═══════════════════════════════════════════════════════
        if profile == "work":
            exe = default_chrome
        else:
            exe = dev_chrome if os.path.exists(dev_chrome) else default_chrome

        if exe and os.path.exists(exe):
            subprocess.Popen([exe, url])
        else:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)

        return f"Opened {url}, Boss."

    if action == "play_spotify":
        query = params.get("query", "")
        try:
            from spotify_controller import play_song
            result = play_song(query)
            return result
        except Exception:
            pass
        from tools.windows_tools import play_spotify
        return play_spotify(query=query)

    if action == "play_playlist":
        pl_name = params.get("name", "tired")
        try:
            from spotify_controller import play_playlist
            return play_playlist(pl_name)
        except Exception:
            pass
        import subprocess
        PLAYLISTS = {
            "tired": "https://open.spotify.com/playlist/6dhvXHh0skhIQm2tL0uJYP?si=8301a4a249674b0e",
        }
        url = PLAYLISTS.get(pl_name.lower(), list(PLAYLISTS.values())[0])
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        return f"Opened your {pl_name} playlist, Boss."

    if action == "delete_desktop_file":
        from tools.windows_tools import delete_file_on_desktop
        return delete_file_on_desktop(params.get("filename", ""))

    if action == "open_app":
        app = params.get("app", "").lower().strip()
        if app in ("vscode", "visual studio code", "code"):
            import subprocess, os
            uname = os.environ.get("USERNAME", "")
            vscode_paths = [
                "C:\\Users\\" + uname + "\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
                "C:\\Program Files\\Microsoft VS Code\\Code.exe",
                "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe",
            ]
            for vp in vscode_paths:
                if os.path.exists(vp):
                    try:
                        subprocess.Popen([vp])
                        return "VSCode opened, Boss."
                    except Exception:
                        continue
            try:
                subprocess.Popen(["code"], shell=True)
                return "VSCode opened, Boss."
            except Exception as e:
                return f"Couldn't open VSCode: {e}"
        try:
            from tools.windows_tools import open_application
            return open_application(app)
        except ImportError:
            import subprocess
            try:
                subprocess.Popen([app], shell=True)
                return f"Opened {app}, Boss."
            except Exception as e:
                return f"Couldn't open {app}: {e}"

    if action == "open_explorer":
        import subprocess
        path = params.get("path", "E:\\")
        try:
            subprocess.Popen(["explorer", path])
            return f"Opened File Explorer at {path}"
        except Exception as e:
            return f"Couldn't open explorer: {e}"

    if action in ("music_pause", "music_resume"):
        try:
            from spotify_controller import pause_music
            return pause_music()
        except Exception as e:
            return f"Music control failed: {e}"

    if action == "music_next":
        try:
            from spotify_controller import next_track
            return next_track()
        except Exception as e:
            return f"Couldn't skip: {e}"

    if action == "music_prev":
        try:
            from spotify_controller import prev_track
            return prev_track()
        except Exception as e:
            return f"Couldn't go back: {e}"

    if action == "music_stop":
        try:
            from spotify_controller import stop_music
            return stop_music()
        except Exception as e:
            return f"Couldn't stop Spotify: {e}"

    if action == "create_code_file":
        try:
            from oi_runner import create_file_with_code
            return create_file_with_code(params.get("prompt", ""))
        except Exception as e:
            return f"File creation failed: {e}"

    if action == "oi_task":
        try:
            from oi_runner import run_oi_task
            return run_oi_task(params.get("prompt", ""))
        except Exception as e:
            return f"Open Interpreter error: {e}"

    if action == "create_file_in_folder":
        folder    = params.get("folder", "")
        filename  = params.get("filename", "main.py")
        content_text = params.get("content", "")
        try:
            import os
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content_text)
            return f"Created {filename} inside {os.path.basename(folder)}."
        except Exception as e:
            return f"Could not create file: {e}"

    return f"Tool '{action}' not implemented yet."