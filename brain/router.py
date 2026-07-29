"""
brain/router.py — STRIX v4.4
==============================
Multi-LLM routing:
  phi3         → chat / greetings / quick answers
  llama3.1     → reasoning / planning / explain / complex
  qwen2.5-coder → ALL code (Python, Java, C++, HTML, CSS, backend)
  qwen2.5-coder → dev (lazy-dev mode: copy-paste ready, no fluff)
"""

import os
import sys
import subprocess
import time

_BRAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_BRAIN_DIR)

for _p in (_BRAIN_DIR, _ROOT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from models.llm_interface import (
    call_chat_model, call_reasoning_model, call_coding_model,
    call_frontend_model, call_backend_model, call_planning_model,
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

# ── System prompts ─────────────────────────────────────────────

PROMPT_CHAT = (
    "[INST] You are STRIX, a sharp and intelligent AI assistant. " + _IDENTITY +
    "Keep replies SHORT — max 2 sentences. "
    "No bullet points, no markdown, no special symbols. [/INST]\n\n"
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
    "Follow best practices. Add comments. No extra explanation unless asked. "
    "NEVER mention ASUS, ROG, or gaming PC.\n\n"
)

# ── NEW: Lazy Dev prompt ───────────────────────────────────────
PROMPT_LAZY_DEV = (
    "You are STRIX, an AI assistant built specifically for lazy developers. " + _IDENTITY +
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

TOOL_ACTIONS = {
    "get_weather","get_news","get_system_status",
    "search_file","read_file","directory_tree",
    "create_java_project","create_c_project","create_cpp_project",
    "create_python_project","list_projects",
    "remember_preference","get_preferences",
    "create_desktop_file","create_desktop_folder",
    "list_desktop","delete_desktop_file","open_app","open_explorer",
    "get_crypto","get_top_crypto","get_joke",
    "get_nasa","get_ip_info","get_exchange",
    "wiki_search","get_github",
    "create_file_in_folder",
    "play_spotify", "play_playlist", "search_files", "open_url",
    "create_code_file", "oi_task",
    "music_pause", "music_resume", "music_next", "music_prev", "music_stop",
}

# ── Language detector ─────────────────────────────────────────
_LANG_KEYWORDS = {
    "java":        "Java",
    "kotlin":      "Kotlin",
    "c++":         "C++",
    "cpp":         "C++",
    "c#":          "C#",
    "csharp":      "C#",
    "javascript":  "JavaScript",
    "typescript":  "TypeScript",
    "nodejs":      "JavaScript (Node.js)",
    " node ":      "JavaScript (Node.js)",
    "golang":      "Go",
    " go ":        "Go",
    "rust":        "Rust",
    "php":         "PHP",
    "swift":       "Swift",
    "ruby":        "Ruby",
    "scala":       "Scala",
    "dart":        "Dart",
    "flutter":     "Dart (Flutter)",
    "perl":        "Perl",
    "matlab":      "MATLAB",
    " sql":        "SQL",
    "bash":        "Bash",
    "shell":       "Shell/Bash",
    ".java":       "Java",
    ".js":         "JavaScript",
    ".ts":         "TypeScript",
    ".kt":         "Kotlin",
    ".cpp":        "C++",
    ".cs":         "C#",
    ".go":         "Go",
    ".rs":         "Rust",
    ".rb":         "Ruby",
    ".php":        "PHP",
    ".swift":      "Swift",
    "python":      "Python",
    ".py":         "Python",
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

    return _route_to_model(task.get("description",""), "chat", stream=stream)


def _route_to_model(prompt: str, model_key: str, stream: bool = False):
    """
    Route prompt to correct model.
    Includes recent conversation context from Obsidian / SQLite memory.
    """
    for attempt in range(5):
        if is_ollama_running(retries=1, wait=0):
            break
        wait = 3 if attempt < 3 else 6
        print(f"[Router] Waiting for Ollama {wait}s (try {attempt+1}/5)...")
        time.sleep(wait)
    else:
        msg = "STRIX offline. Please start Ollama with: ollama serve"
        return iter([msg]) if stream else msg

    # Fetch recent conversation context for natural follow-ups (e.g. "now in java")
    try:
        from memory.obsidian_memory import get_obsidian_memory
        mem = get_obsidian_memory()
        history = mem.get_recent_context(limit=6)
    except Exception:
        history = ""

    if history:
        full_prompt_text = f"\n--- RECENT CONVERSATION HISTORY ---\n{history}\n--- END CONVERSATION HISTORY ---\n\nUser Request: {prompt}"
    else:
        full_prompt_text = prompt

    if model_key == "chat":
        full = PROMPT_CHAT + full_prompt_text
        return call_chat_model(full, stream=stream)

    elif model_key == "reasoning":
        full = PROMPT_REASON + full_prompt_text
        return call_reasoning_model(full, stream=stream)

    elif model_key == "coding":
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this code in {lang} ONLY.\n" if lang else ""
        full = PROMPT_CODE + lang_note + full_prompt_text
        return call_coding_model(full, stream=stream)

    elif model_key == "frontend":
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this in {lang} ONLY.\n" if lang else ""
        full = PROMPT_FRONTEND + lang_note + full_prompt_text
        return call_frontend_model(full, stream=stream)

    elif model_key == "backend":
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this in {lang} ONLY.\n" if lang else ""
        full = PROMPT_BACKEND + lang_note + full_prompt_text
        return call_backend_model(full, stream=stream)

    elif model_key == "planning":
        full = PROMPT_REASON + full_prompt_text
        return call_planning_model(full, stream=stream)

    # ── NEW: lazy dev route ───────────────────────────────────
    elif model_key == "dev":
        lang = _detect_language(prompt)
        lang_note = f"\nIMPORTANT: Write this in {lang} ONLY.\n" if lang else ""
        full = PROMPT_LAZY_DEV + lang_note + full_prompt_text
        return call_coding_model(full, stream=stream)

    else:
        full = PROMPT_CHAT + full_prompt_text
        return call_chat_model(full, stream=stream)


def _run_tool(action: str, params: dict) -> str:

    if action == "get_weather":
        from api.weather import format_weather
        return format_weather(params.get("city"))

    if action == "get_news":
        from api.news import format_news
        return format_news(params.get("category","technology"), params.get("count",5))

    if action == "get_system_status":
        from tools.system_tools import get_system_summary
        return get_system_summary()

    if action == "wiki_search":
        from api.extras import search_wikipedia
        return search_wikipedia(params.get("query",""))

    if action == "get_crypto":
        from api.extras import get_crypto_price
        return get_crypto_price(params.get("coin","bitcoin"))

    if action == "get_top_crypto":
        from api.extras import get_top_crypto
        return get_top_crypto()

    if action == "get_joke":
        try:
            import pyjokes
            return f"Here is one for you Boss — {pyjokes.get_joke(language='en', category='neutral')}"
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
        return get_exchange_rate(params.get("from","USD"), params.get("to","INR"))

    if action == "get_github":
        from api.extras import get_github_profile
        username = params.get("username","")
        if not username:
            return "Please tell me the GitHub username Boss."
        return get_github_profile(username)

    if action in ("search_file", "search_files"):
        from tools.search_tools import search_files, format_search_results
        query       = params.get("query", "")
        search_path = params.get("search_path", None)
        EXT_WORDS = {
            "python": ".py", "javascript": ".js", "js file": ".js",
            "typescript": ".ts", "html": ".html", "css": ".css",
            "java": ".java", "cpp": ".cpp", "c++": ".cpp",
            "text": ".txt", "txt": ".txt", "json": ".json",
            "xml": ".xml", "csv": ".csv", "pdf": ".pdf",
        }
        extensions = None
        q_lower = query.lower()
        for word, ext in EXT_WORDS.items():
            if word in q_lower:
                extensions = [ext]
                query = q_lower.replace(word, "").replace("file", "").strip(" .")
                break
        results = search_files(query=query, search_dir=search_path, extensions=extensions)
        return format_search_results(results)

    if action == "read_file":
        from tools.search_tools import read_file
        return read_file(params.get("path",""))

    if action == "directory_tree":
        from tools.search_tools import get_directory_tree
        return get_directory_tree(params.get("path","."))

    if action == "create_java_project":
        from tools.project_tools import create_java_project
        return create_java_project(params.get("name","MyProject"))

    if action == "create_c_project":
        from tools.project_tools import create_c_project
        return create_c_project(params.get("name","MyProject"))

    if action == "create_cpp_project":
        from tools.project_tools import create_cpp_project
        return create_cpp_project(params.get("name","MyProject"))

    if action == "create_python_project":
        from tools.project_tools import create_python_project
        return create_python_project(params.get("name","MyProject"))

    if action == "list_projects":
        from tools.project_tools import list_projects
        return list_projects()

    if action == "remember_preference":
        from memory.memory_db import set_preference
        key = params.get("key",""); val = params.get("value","")
        if key:
            set_preference(key, val)
            return "Got it Boss, I will remember that."
        return "No key provided."

    if action == "get_preferences":
        from memory.memory_db import get_all_preferences
        prefs = get_all_preferences()
        if not prefs:
            return "No preferences saved yet."
        return "Your preferences: " + ", ".join(f"{k} is {v}" for k,v in prefs.items())

    if action == "create_desktop_file":
        from brain.planner import DESKTOP
        desktop = DESKTOP
        fname   = params.get("filename", "file.txt")
        path    = os.path.join(desktop, fname)
        content = params.get("content", "")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File '{fname}' created on Desktop."
        except Exception as e:
            return f"Could not create file: {e}"

    if action == "create_desktop_folder":
        from brain.planner import DESKTOP
        desktop = DESKTOP
        name    = params.get("foldername", "NewFolder")
        path    = os.path.join(desktop, name)
        try:
            os.makedirs(path, exist_ok=True)
            return f"Folder '{name}' created on Desktop."
        except Exception as e:
            return f"Could not create folder: {e}"

    if action == "list_desktop":
        from brain.planner import DESKTOP
        desktop = DESKTOP
        try:
            items = os.listdir(desktop)
            if not items:
                return "Desktop is empty."
            return "Desktop files:\n" + "\n".join(f"  • {i}" for i in sorted(items))
        except Exception as e:
            return f"Could not list desktop: {e}"

    if action == "delete_desktop_file":
        from brain.planner import DESKTOP
        desktop = DESKTOP
        fname   = params.get("filename","")
        path    = os.path.join(desktop, fname)
        try:
            if os.path.exists(path):
                os.remove(path)
                return f"Deleted '{fname}' from Desktop."
            return f"File '{fname}' not found on Desktop."
        except Exception as e:
            return f"Could not delete file: {e}"

    if action == "open_url":
        url = params.get("url", "")
        if not url:
            return "No URL provided."

        import webbrowser
        webbrowser.open(url)
        return f"Opened {url}, Boss."

    if action == "play_spotify":
        try:
            from spotify_controller import play_song
            return play_song(params.get("query",""))
        except Exception as e:
            return f"Spotify error: {e}"

    if action == "play_playlist":
        pl_name = params.get("name", "tired")
        try:
            from spotify_controller import play_playlist
            return play_playlist(pl_name)
        except Exception:
            pass
        PLAYLISTS = {
            "tired": "https://open.spotify.com/playlist/6dhvXHh0skhIQm2tL0uJYP",
        }
        url = PLAYLISTS.get(pl_name.lower(), list(PLAYLISTS.values())[0])
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        return f"Opened your {pl_name} playlist, Boss."

    if action == "open_app":
        app = params.get("app", "").lower().strip()
        if app in ("vscode", "visual studio code", "code"):
            uname = os.environ.get("USERNAME", "")
            for vp in [
                f"C:\\Users\\{uname}\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
                "C:\\Program Files\\Microsoft VS Code\\Code.exe",
                "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe",
            ]:
                if os.path.exists(vp):
                    subprocess.Popen([vp])
                    return "VSCode opened, Boss."
            try:
                subprocess.Popen(["code"], shell=True)
                return "VSCode opened, Boss."
            except Exception as e:
                return f"Couldn't open VSCode: {e}"
        try:
            subprocess.Popen([app], shell=True)
            return f"Opened {app}, Boss."
        except Exception as e:
            return f"Couldn't open {app}: {e}"

    if action == "open_explorer":
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
            return create_file_with_code(params.get("prompt",""))
        except Exception as e:
            return f"File creation failed: {e}"

    if action == "create_file_in_folder":
        folder   = params.get("folder","")
        filename = params.get("filename","main.py")
        content  = params.get("content","")
        try:
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Created {filename} inside {os.path.basename(folder)}."
        except Exception as e:
            return f"Could not create file: {e}"

    return f"Tool '{action}' not implemented yet."