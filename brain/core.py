"""
brain/core.py — STRIX v4.1
============================
CHANGE: _classify_llm now routes coding/dev questions to "dev"
        (lazy dev mode: copy-paste ready, no fluff, full boilerplate)

Routing priority:
  1. Desktop/file/folder tasks  → ALWAYS direct tool, never LLM
  2. Multi-step planner         → complex requests
  3. Info tools                 → weather, news, system, etc
  4. LLM routes                 → chat, reasoning, dev (lazy-dev), coding
"""

import os, sys, re
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    load_dotenv(_env_path)
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from brain.input_processor import process_text_input
from brain.executor        import execute_plan
from brain.planner         import build_plan, is_multi_step, _get_starter, DESKTOP, EXT_MAP
from memory.memory_db      import save_message, get_recent_messages, initialize_db

WAKE_WORDS = [
    "hey strix","ok strix","strix wake up","wake up strix",
    "wake up","yo strix","strix","open strix","strix open",
    "start strix","launch strix","hello strix","hi strix",
]

# ── Speech recognition corrections ───────────────────────────
SPEECH_FIXES = [
    ("google home",         "google chrome"),
    ("open home",           "open chrome"),
    ("good home",           "google chrome"),
    ("good chrome",         "google chrome"),
    ("crome",               "chrome"),
    ("chrom ",              "chrome "),
    ("shut dan",            "shutdown"),
    ("shut dawn",           "shutdown"),
    ("shot down",           "shutdown"),
    ("note pad",            "notepad"),
    ("note pet",            "notepad"),
    ("visual code",         "vscode"),
    ("vs cold",             "vscode"),
    ("v s code",            "vscode"),
    ("calclulator",         "calculator"),
    ("calculater",          "calculator"),
    ("you tube",            "youtube"),
    ("disc cord",           "discord"),
    ("what sap",            "whatsapp"),
    ("what's up app",      "whatsapp"),
    ("open cmd",            "open cmd"),
    ("command prompt",      "cmd"),
    ("you tube",            "youtube"),
    ("u tube",              "youtube"),
    ("you toob",            "youtube"),
    ("git hub",             "github"),
    ("git hut",             "github"),
    ("git hat",             "github"),
    ("git hot",             "github"),
    ("open git hut",        "open github"),
    ("open git hat",        "open github"),
    ("open git hot",        "open github"),
    ("you tuber",           "youtube"),
    ("power shell",         "powershell"),
    ("powers hell",         "powershell"),
    ("power shale",         "powershell"),
    ("spot if I",           "spotify"),
    ("spot a fly",          "spotify"),
    ("spot if eye",         "spotify"),
    ("specify",             "spotify"),
    ("spotfiy",             "spotify"),
    ("spotfy",              "spotify"),
    ("spot fi",             "spotify"),
    ("spotifi",             "spotify"),
    ("spot five",           "spotify"),
    ("spot free",           "spotify"),
    ("spot a fee",          "spotify"),
    ("spot a fire",         "spotify"),
    ("open specify",        "open spotify"),
    ("play specify",        "play spotify"),
    ("launch specify",      "launch spotify"),
    ("play this song",      "play song"),
    ("play the song",       "play song"),
    ("open the song",       "play song"),
    ("open this song",      "play song"),
    ("put on",              "play"),
    ("open couture",        "open youtube"),
    ("find older",          "find folder"),
    ("find a older",        "find folder"),
    ("find the older",      "find the folder"),
    ("search older",        "search folder"),
    ("create older",        "create folder"),
    ("make older",          "make folder"),
    ("open older",          "open folder"),
    ("cava",                "java"),
    ("java practical",      "java practical"),
    ("kava",                "java"),
    ("hava",                "java"),
    ("show aime",           "show anime"),
    ("show aim",            "show anime"),
    ("open aime",           "open anime"),
    ("open aim",            "open anime"),
    ("show any me",         "show anime"),
    ("watch aime",          "watch anime"),
    ("show an ime",         "show anime"),
    ("open any me",         "open anime"),
    ("open you two",        "open youtube"),
    ("open you too",        "open youtube"),
    ("open utube",          "open youtube"),
    ("play couture",        "play youtube"),
    ("couture",             "youtube"),
    ("you two",             "youtube"),
    ("you too",             "youtube"),
    ("open get hub",        "open github"),
    ("open get up",         "open github"),
    ("get hub",             "github"),
    ("get up",              "github"),
    ("open chat gbd",       "open chatgpt"),
    ("open chat gb t",      "open chatgpt"),
    ("open shat gpt",       "open chatgpt"),
    ("chat gb t",           "chatgpt"),
    ("chat gbd",            "chatgpt"),
    ("jimmy knee",          "gemini"),
    ("jimminy",             "gemini"),
    ("jim any",             "gemini"),
    ("this cord",           "discord"),
    ("disc court",          "discord"),
    ("what stop",           "whatsapp"),
    ("what's app",          "whatsapp"),
    ("what zap",            "whatsapp"),
    ("spot a pie",          "spotify"),
    ("spot a guy",          "spotify"),
    ("spit a fire",         "spotify"),
    ("open email",          "open gmail"),
    ("open mail",           "open gmail"),
    ("open my email",       "open gmail"),
    ("open my mail",        "open gmail"),
    ("check email",         "open gmail"),
    ("check mail",          "open gmail"),
    ("check my email",      "open gmail"),
    ("check my mail",       "open gmail"),
    ("go to email",         "open gmail"),
    ("go to mail",          "open gmail"),
    ("open e mail",         "open gmail"),
    ("open g mail",         "open gmail"),
    ("open jee mail",       "open gmail"),
    ("open jamail",         "open gmail"),
    ("open you tube",       "open youtube"),
    ("open utube",          "open youtube"),
    ("open chat gpt",       "open chatgpt"),
    ("open chat g p t",     "open chatgpt"),
    ("open jet gpt",        "open chatgpt"),
    ("play co ",            "play co2 "),
    ("play co$",            "play co2"),
    ("open co ",            "play co2 "),
    ("play eminem",         "play eminem"),
    ("play mine",           "play eminem"),
    ("play my name",        "play eminem"),
    ("play minimum",        "play eminem"),
    ("play ameen",          "play eminem"),
    ("play enemy",          "play eminem"),
    ("play m&m",            "play eminem"),
    ("play minecraft playlist", "play minecraft playlist"),
]

_SONG_NUMBER_FIXES = {
    "play co":    "play co2",
    "open co":    "play co2",
    "play co ":   "play co2",
}

_APP_NAMES = [
    "spotify", "chrome", "notepad", "calculator", "pycharm",
    "powershell", "discord", "telegram", "wallpaper engine",
    "eclipse", "vscode", "steam", "firefox", "brave",
    "explorer", "settings", "taskmanager", "vlc", "obs", "zoom",
    "youtube", "github", "chatgpt", "gemini", "whatsapp",
]

_WEB_NAMES = {
    "youtube":  ["couture", "utube", "you two", "you too", "you tube", "you toob",
                 "utoo", "utwo", "u2", "yotube"],
    "github":   ["get hub", "get up", "git up", "githup", "gitub", "gethub"],
    "chatgpt":  ["chat gbd", "chat gb t", "shat gpt", "chatgbt", "chat gbt"],
    "gemini":   ["jimmy knee", "jimminy", "jim any", "jiminy", "jimminy cricket"],
    "spotify":  ["specify", "spot if I", "spot a fly", "spot a fire", "spot five",
                 "spotfi", "spotifi", "spotfiy", "spot a guy", "spot a pie"],
    "whatsapp": ["what's up app", "what stop", "what zap", "what's app", "whatsap"],
    "discord":  ["this cord", "disc cord", "disc court", "discort"],
}

def _web_name_fix(tl: str) -> str:
    for correct, mishearings in _WEB_NAMES.items():
        for m in mishearings:
            if m in tl:
                tl = tl.replace(m, correct)
    return tl

def _fuzzy_app_fix(tl: str) -> str:
    tl = _web_name_fix(tl)
    words = tl.split()
    result = []
    i = 0
    while i < len(words):
        word = words[i]
        replaced = False
        for app in _APP_NAMES:
            if _edit_dist(word, app) <= 2 and len(word) >= 4:
                result.append(app)
                replaced = True
                break
        if not replaced:
            result.append(word)
        i += 1
    return " ".join(result)

def _edit_dist(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 3: return 99
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i-1] == b[j-1] else 1 + min(prev, dp[j], dp[j-1])
            prev = temp
    return dp[n]

def _fix_speech(text: str) -> str:
    tl = text.lower().strip()
    for wrong, right in _SONG_NUMBER_FIXES.items():
        if tl == wrong.strip() or tl == wrong.strip() + " ":
            tl = right
            break
    for wrong, right in SPEECH_FIXES:
        if wrong in tl:
            tl = tl.replace(wrong, right)
    is_app_cmd  = any(tl.startswith(w) for w in ["open ", "launch ", "start ", "run "])
    is_play_cmd = tl.startswith("play ")
    if is_app_cmd:
        tl = _fuzzy_app_fix(tl)
    elif is_play_cmd:
        tl = _web_name_fix(tl)
    return tl


FAST_ROUTES = {
    "weather": {"tasks":[{"id":1,"action":"get_weather","params":{}}],"summary":"weather"},
    "news":    {"tasks":[{"id":1,"action":"get_news","params":{"category":"technology","count":5}}],"summary":"news"},
    "system":  {"tasks":[{"id":1,"action":"get_system_status","params":{}}],"summary":"system"},
    "joke":    {"tasks":[{"id":1,"action":"get_joke","params":{}}],"summary":"joke"},
    "nasa":    {"tasks":[{"id":1,"action":"get_nasa","params":{}}],"summary":"nasa"},
    "ip":      {"tasks":[{"id":1,"action":"get_ip_info","params":{}}],"summary":"ip"},
}


def _task(prompt, model="reasoning"):
    return {"tasks":[{"id":1,"action":"llm_response","description":prompt,
                      "params":{"prompt":prompt,"model":model}}],"summary":model}


def _strip_wake_word(text):
    tl = text.lower().strip()
    for ww in sorted(WAKE_WORDS, key=len, reverse=True):
        if tl.startswith(ww):
            stripped = text[len(ww):].strip(" ,.")
            return stripped if stripped else text
    return text


FILE_VERBS    = {"make","create","build","write","generate","add","put","new","give"}
FILE_NOUNS    = {"file","folder","directory","project"}
FILE_LANGS    = {"python","py","java","javascript","js","html","css","typescript",
                 "ts","cpp","c++","c","sql","react","node","php","kotlin","flutter"}
DESKTOP_WORDS = {"desktop","desktopp","desktoppp","desk top"}

CODE_VERBS    = {"write","generate","create","make","build","show","give","code"}
CODE_NOUNS    = {"code","program","function","class","script","algorithm","snippet"}

REASON_WORDS  = {"why","explain","how does","what is","who is","tell me about",
                 "difference","compare","help me understand","describe","meaning",
                 "analyse","analyze","suggest","recommend","advice","should i",
                 "what should","plan","what are","how can","is it","are there"}

CHAT_WORDS    = {"hello","hi","hey","good morning","good night","good evening",
                 "how are you","what's up","who are you","thanks","thank you",
                 "ok","okay","bye","goodbye","nice","what is your name",
                 "are you","do you","can you"}

# ── NEW: lazy dev trigger words ───────────────────────────────
# These phrases signal "I want ready-to-use code, not theory"
DEV_WORDS = {
    "fix this", "fix my", "fix the", "debug", "error in",
    "not working", "broken", "crashes", "bug in", "issue with",
    "how to implement", "how do i make", "boilerplate", "template for",
    "starter code", "full code", "complete code", "working code",
    "copy paste", "ready to use", "example of", "example for",
    "give me the full", "give me a working", "build me",
    "make me a", "create me a", "write me the",
    "how to set up", "setup", "install and use",
    "how to connect", "how to integrate",
}


def _has(tl, words):
    return any(w in tl for w in words)


def _extract_quoted_name(text):
    m = re.search(r'["\']([^"\']+)["\']', text)
    return m.group(1).strip() if m else None


def _extract_name_after(tl, keywords):
    for kw in sorted(keywords, key=len, reverse=True):
        idx = tl.find(kw)
        if idx != -1:
            after = tl[idx+len(kw):].strip()
            words = after.split()
            STOP = {"a","an","the","on","in","it","to","and","with","as",
                    "file","folder","python","html","css","js","please"}
            name_parts = [w for w in words[:4] if w not in STOP]
            if name_parts:
                return "_".join(name_parts[:3])
    return None


def _extract_file_name(tl, original):
    name = _extract_quoted_name(original)
    if name:
        return name.replace(" ", "_")
    name = _extract_name_after(tl, ["named ","called ","name it ","name the file ","name "])
    if name:
        return name.replace(" ", "_")
    m = re.search(r'(?:name|call)\s+it\s+([a-z0-9_\-]+)', tl)
    if m:
        return m.group(1)
    return None


def _detect_ext(tl):
    for lang, ext in EXT_MAP.items():
        if lang in tl:
            return ext
    return ".py"


def _classify_llm(tl):
    """
    Pick which LLM model to use.
    UPDATED: dev-intent queries → "dev" (lazy dev mode, copy-paste ready)
             pure code generation stays "coding"
             reasoning/chat unchanged
    """
    # Frontend code
    if _has(tl, {"html","css","webpage","website","frontend","react","ui","interface","bootstrap"}):
        if _has(tl, {"write","create","make","build","generate","code","design"}):
            return "frontend"

    # Backend code
    if _has(tl, {"backend","api","server","database","django","flask","spring",
                 "express","mysql","mongodb","rest","fastapi"}):
        if _has(tl, {"write","create","make","build","generate","code","connect"}):
            return "backend"

    # ── Lazy dev route — fix/debug/boilerplate/setup requests ─
    # These need full working code, not theory
    if _has(tl, DEV_WORDS):
        print("[STRIX] → Lazy dev route (copy-paste mode)")
        return "dev"

    # General code generation
    has_code_noun = _has(tl, CODE_NOUNS)
    has_lang      = any(l in tl for l in FILE_LANGS)
    has_code_verb = _has(tl, CODE_VERBS)
    if (has_lang and has_code_verb) or (has_code_noun and has_code_verb):
        return "dev"   # all code requests → lazy dev mode

    # Reasoning
    if any(w in tl for w in REASON_WORDS):
        return "reasoning"

    # Chat
    if any(w in tl for w in CHAT_WORDS):
        return "chat"

    return "reasoning"


def _extract_name(tl, skip_words):
    IGNORE = {"make","create","new","a","an","the","on","in","it","to","and",
              "me","my","please","write","put","some","code","file","folder",
              "desktop","named","called","name","with","simple","basic","program",
              "python","java","javascript","html","css","script","just","also",
              "inside","into","at","of","for","give","build","generate"}
    for sw in skip_words:
        for w in sw.split(): IGNORE.add(w.lower())
    words = tl.split()
    name_words = [w for w in words if w.lower() not in IGNORE and len(w) > 1]
    if name_words:
        result = "_".join(name_words[:3])
        for ext in [".py",".java",".js",".html",".txt",".cpp",".c"]:
            result = result.replace(ext,"")
        return result.strip("_")
    return ""


class StrixBrain:
    def __init__(self):
        initialize_db()
        print("[STRIX Brain] Ready.")
        print("[STRIX] Models: phi3=chat | llama3.1=reasoning | qwen2.5-coder=dev/code")

    def process(self, raw: str, stream: bool = False):
        if not raw.strip():
            msg = "Please say something Boss."
            return iter([msg]) if stream else msg

        raw       = _strip_wake_word(raw)
        processed = process_text_input(raw)
        text      = processed["corrected"]
        tl        = _fix_speech(text.lower())
        text      = tl
        save_message("user", text)
        plan      = None

        print(f"[STRIX] Input: '{text}'")

        # ── Priority 0: KILL ──────────────────────────────────
        KILL_WORDS = {
            "kill","kill yourself","kill strix",
            "self destruct","self-destruct","delete yourself"
        }
        if any(w == tl.strip() or tl.startswith(w) for w in KILL_WORDS):
            return "STRIX_KILL"

        # ── Priority 0: SHUTDOWN ──────────────────────────────
        SHUTDOWN_WORDS = {
            "shutdown","shut down","close yourself","close strix",
            "goodbye strix","bye strix","exit","quit","turn off",
            "go offline","sleep","shut up and close","terminate",
            "power off","see you later","goodnight strix",
            "good night strix","shut yourself","close yourself down",
        }
        if any(w in tl for w in SHUTDOWN_WORDS):
            save_message("assistant", "Goodbye Boss. STRIX going offline.")
            return "STRIX_SHUTDOWN"

        # ── Priority 0: CREATOR ───────────────────────────────
        CREATOR_WORDS = {
            "who made you","who created you","who built you",
            "who is your creator","who are you","your creator",
            "who made strix","who created strix","who is prahlad",
            "your maker","who designed you"
        }
        if any(w in tl for w in CREATOR_WORDS):
            return "I was created by Prahlad, Boss. He built me from scratch."

        # ── Priority 1: FILESYSTEM ────────────────────────────
        is_file_verb = _has(tl, FILE_VERBS)
        is_file_noun = _has(tl, FILE_NOUNS)
        is_lang      = any(l in tl for l in FILE_LANGS)
        is_desktop   = _has(tl, DESKTOP_WORDS) or "desktop" in tl

        if is_file_verb and "file" in tl and (is_desktop or is_lang):
            fname = _extract_file_name(tl, text)
            ext   = _detect_ext(tl)
            if fname and not re.search(r'\.\w+$', fname):
                fname = fname + ext
            fname = fname or ("main" + ext)
            fname = fname.replace(" ","_")
            starter = _get_starter(fname, ext.lstrip("."))
            dest = os.path.join(DESKTOP, fname)
            plan = {"tasks":[{"id":1,"action":"create_file_at_path",
                               "params":{"path": dest, "content": starter}}],
                    "summary":"file"}

        elif is_file_verb and ("folder" in tl or "directory" in tl) and is_desktop:
            name = _extract_file_name(tl, text) or _extract_name(tl, ["folder","directory"])
            name = name or "NewFolder"
            dest = os.path.join(DESKTOP, name)
            plan = {"tasks":[{"id":1,"action":"create_folder_path",
                               "params":{"path": dest}}],
                    "summary":"folder"}

        elif is_multi_step(tl) and (is_file_verb or is_file_noun):
            plan = build_plan(text)

        elif is_file_verb and ("folder" in tl or "directory" in tl):
            name = _extract_file_name(tl, text) or _extract_name(tl, ["folder","directory"])
            name = name or "NewFolder"
            dest = os.path.join(DESKTOP, name)
            plan = {"tasks":[{"id":1,"action":"create_folder_path",
                               "params":{"path": dest}}],
                    "summary":"folder"}

        elif any(t in tl for t in {
                "work time", "get on work", "work mode", "start working",
                "focus mode", "lets work", "let's work", "time to work",
                "start work", "work session", "get to work", "begin work",
                "office mode", "coding time", "code time", "dev mode",
            }):
            plan = {
                "tasks": [
                    {"id": 1, "action": "open_app",     "params": {"app": "vscode"},          "description": "Open VSCode"},
                    {"id": 2, "action": "open_url",     "params": {"url": "https://mail.google.com/mail/u/0/#inbox", "profile": "work"}, "description": "Open work Gmail"},
                    {"id": 3, "action": "open_explorer","params": {"path": "E:\\"},            "description": "Open E: drive"},
                    {"id": 4, "action": "open_url",     "params": {"url": "https://claude.ai/new", "profile": "work"}, "description": "Open Claude new chat"},
                ],
                "summary": "work_mode"
            }

        elif any(t in tl for t in {
                "recommend", "recommendation", "what anime", "which anime",
                "best anime", "top anime", "anime to watch", "anime list",
                "anime idea", "anime ideas", "explore anime", "find anime",
                "new anime", "good anime", "popular anime", "trending anime",
                "anime suggestion", "anime suggestions", "suggest anime",
                "everythingmoe", "anime info", "about anime",
            }):
            plan = {"tasks":[{"id":1,"action":"open_url",
                               "params":{"url":"https://everythingmoe.com/","profile":"main"}}],
                    "summary":"url"}

        elif any(t in tl for t in {
                "anime", "watch anime", "show anime", "open anime",
                "show me anime", "animewatch", "aniwatch",
            }):
            plan = {"tasks":[{"id":1,"action":"open_url",
                               "params":{"url":"https://aniwatchtv.to/home","profile":"main"}}],
                    "summary":"url"}

        elif any(w in tl for w in ["my playlist","open playlist","play playlist",
                                    "open my playlist","play my playlist",
                                    "open tired","play tired","tired playlist",
                                    "play the playlist"]):
            KNOWN_PLAYLISTS = ["tired"]
            pl_name = next((n for n in KNOWN_PLAYLISTS if n in tl), "tired")
            plan = {"tasks":[{"id":1,"action":"play_playlist",
                               "params":{"name": pl_name}}],
                    "summary":"playlist"}

        elif "spotify" in tl and _has(tl, {"open","launch","start"}):
            plan = {"tasks":[{"id":1,"action":"play_spotify",
                               "params":{"query": ""}}],
                    "summary":"spotify"}

        elif any(w in tl for w in ["play ","put on ","play song","play artist",
                                    "play music","open song","search spotify",
                                    "play on spotify","play this song"]):
            song = tl
            for phrase in ["play song","play artist","play on spotify","play music",
                           "play this song","open song","search spotify","put on","play "]:
                if phrase in song:
                    song = song[song.find(phrase)+len(phrase):].strip()
                    break
            song = song.strip(" .?\"'")
            plan = {"tasks":[{"id":1,"action":"play_spotify",
                               "params":{"query": song}}],
                    "summary":"spotify"}

        elif any(tl.startswith(w) for w in ["play ","play song ","play the ","play artist "]) \
             or any(w in tl for w in ["play song","open the song","open this song",
                                       "put on","play some","play me"]):
            song = tl
            for phrase in ["play song","play the song","play artist","open the song",
                           "open this song","play some","play me","put on","play "]:
                if phrase in song:
                    song = song[song.find(phrase)+len(phrase):].strip()
                    break
            song = song.strip(" .?'\" ") or ""
            plan = {"tasks":[{"id":1,"action":"play_spotify",
                               "params":{"query": song}}],
                    "summary":"spotify"}

        elif _has(tl, {"open","go to","launch","visit","browse","check"}) and _has(tl, {
                "youtube","facebook","instagram","twitter","x.com","reddit",
                "github","my github","google","whatsapp","netflix","amazon","twitch",
                "stackoverflow","chatgpt","chat gpt","gmail","my gmail","email","my email",
                "gemini","google gemini","linkedin","wikipedia"}):

            _gh_user      = os.environ.get("GITHUB_USERNAME", "prahaldgadekar")
            WORK_URLS = {
                "github":    f"https://github.com/{_gh_user}",
                "my github": f"https://github.com/{_gh_user}",
            }
            MAIN_URLS = {
                "youtube":       "https://www.youtube.com",
                "gmail":         "https://mail.google.com/mail/u/0/#inbox",
                "my gmail":      "https://mail.google.com/mail/u/0/#inbox",
                "email":         "https://mail.google.com/mail/u/0/#inbox",
                "my email":      "https://mail.google.com/mail/u/0/#inbox",
                "chatgpt":       "https://chat.openai.com",
                "chat gpt":      "https://chat.openai.com",
                "gemini":        "https://gemini.google.com",
                "google gemini": "https://gemini.google.com",
                "facebook":      "https://www.facebook.com",
                "instagram":     "https://www.instagram.com",
                "twitter":       "https://www.twitter.com",
                "x.com":         "https://www.x.com",
                "reddit":        "https://www.reddit.com",
                "google":        "https://www.google.com",
                "netflix":       "https://www.netflix.com",
                "amazon":        "https://www.amazon.in",
                "twitch":        "https://www.twitch.tv",
                "stackoverflow": "https://stackoverflow.com",
                "linkedin":      "https://www.linkedin.com",
                "wikipedia":     "https://www.wikipedia.org",
            }

            if "whatsapp" in tl:
                plan = {"tasks":[{"id":1,"action":"open_app","params":{"app":"whatsapp"}}],"summary":"app"}
            else:
                work_key = next((k for k in WORK_URLS if k in tl), "")
                main_key = next((k for k in MAIN_URLS if k in tl), "")
                if work_key:
                    plan = {"tasks":[{"id":1,"action":"open_url",
                                       "params":{"url": WORK_URLS[work_key],"profile": "work"}}],
                            "summary":"url"}
                elif main_key:
                    plan = {"tasks":[{"id":1,"action":"open_url",
                                       "params":{"url": MAIN_URLS[main_key],"profile": "main"}}],
                            "summary":"url"}

        elif _has(tl, {"open","launch","start","run"}) and _has(tl, {
                "notepad","calculator","calc","paint","explorer","file explorer",
                "chrome","google chrome","google home","browser",
                "vscode","vs code","visual studio code","code",
                "cmd","command prompt","terminal","powershell","power shell","pwsh",
                "eclipse","spotify","discord","pycharm","py charm",
                "word","excel","powerpoint","steam","task manager","settings",
                "youtube","vlc","obs","zoom","skype","telegram","whatsapp",
                "wallpaper engine","wallpaper","intellij","android studio",
                "brave","firefox","photoshop","illustrator","premiere","aftereffects"}):
            app = "notepad"
            app_map = {
                "chrome": "chrome", "google chrome": "chrome", "google home": "chrome",
                "browser": "chrome", "notepad": "notepad",
                "calculator": "calculator", "calc": "calculator", "paint": "paint",
                "explorer": "explorer", "file explorer": "explorer",
                "vscode": "vscode", "vs code": "vscode", "visual studio code": "vscode",
                "cmd": "cmd", "command prompt": "cmd", "terminal": "cmd",
                "powershell": "powershell", "power shell": "powershell", "pwsh": "powershell",
                "eclipse": "eclipse", "pycharm": "pycharm", "py charm": "pycharm",
                "wallpaper engine": "wallpaper engine", "wallpaper": "wallpaper engine",
                "android studio": "android studio", "intellij": "intellij",
                "obs": "obs", "vlc": "vlc", "zoom": "zoom", "telegram": "telegram",
                "brave": "brave", "firefox": "firefox",
                "settings": "settings", "setting": "settings",
                "task manager": "taskmgr", "taskmanager": "taskmgr",
                "spotify": "spotify", "discord": "discord",
                "word": "word", "excel": "excel", "powerpoint": "powerpoint", "steam": "steam",
            }
            for key, val in sorted(app_map.items(), key=lambda x: -len(x[0])):
                if key in tl:
                    app = val
                    break
            plan = {"tasks":[{"id":1,"action":"open_app","params":{"app":app}}],"summary":"app"}

        # ── Priority 2: INFO TOOLS ────────────────────────────
        elif _has(tl, {"weather","temperature","rain","humidity","forecast"}):
            plan = FAST_ROUTES["weather"]

        elif _has(tl, {"news","headline","latest news","trending"}):
            plan = FAST_ROUTES["news"]

        elif any(w in tl for w in ["system status","system report","cpu usage",
                                    "ram usage","battery status","show system",
                                    "check system","how is my pc"]):
            plan = FAST_ROUTES["system"]

        elif any(w in tl for w in ["tell me a joke","give me a joke","make me laugh"]):
            plan = FAST_ROUTES["joke"]

        elif any(w in tl for w in ["nasa apod","nasa picture","astronomy picture"]):
            plan = FAST_ROUTES["nasa"]

        elif any(w in tl for w in ["my ip","ip address","internet provider","isp"]):
            plan = FAST_ROUTES["ip"]

        elif _has(tl, {"crypto","bitcoin","ethereum","btc","eth","dogecoin","solana"}):
            coin = "bitcoin"
            for c in ["bitcoin","btc","ethereum","eth","dogecoin","doge","solana","bnb","xrp"]:
                if c in tl: coin = c; break
            action = "get_top_crypto" if ("top" in tl or "list" in tl) else "get_crypto"
            plan = {"tasks":[{"id":1,"action":action,"params":{"coin":coin}}],"summary":"crypto"}

        elif any(w in tl for w in ["exchange rate","currency convert","usd to","inr to"]):
            from_c, to_c = "USD","INR"
            currencies = {"usd":"USD","inr":"INR","eur":"EUR","gbp":"GBP","jpy":"JPY","aud":"AUD"}
            found = [currencies[w] for w in tl.split() if w in currencies]
            if len(found) >= 2: from_c, to_c = found[0], found[1]
            elif len(found) == 1: from_c = found[0]
            plan = {"tasks":[{"id":1,"action":"get_exchange",
                               "params":{"from":from_c,"to":to_c}}],"summary":"exchange"}

        elif _has(tl, {"github","my repos","repository"}):
            user = os.environ.get("GITHUB_USERNAME","prahaldgadekar")
            plan = {"tasks":[{"id":1,"action":"get_github",
                               "params":{"username":user}}],"summary":"github"}

        elif any(w in tl for w in ["list desktop","show desktop","files on desktop"]):
            plan = {"tasks":[{"id":1,"action":"list_desktop","params":{}}],"summary":"desktop"}

        elif any(w in tl for w in ["search for","find file","find folder","where is",
                                    "locate","look for","search file","search folder",
                                    "find the file","find the folder","search my",
                                    "find this","find it","where did i put","find my",
                                    "look up","i need the file","get the file",
                                    "find older","find folder named","find file named",
                                    "search folder named","where is the folder",
                                    "find folder named",
                                    "find python","find javascript","find js file",
                                    "find html file","find css file","find java file",
                                    "find .py","find .js","find .html","find .txt",
                                    "find .json","find .csv","find .pdf","find .cpp",
                                    "find typescript","find text file","find json file",
                                    "show python","show .py","list python files",
                                    ]) or (
                                    tl.startswith("find ") and tl.endswith((" file", " files", ".py", ".js", ".html", ".txt"))
                                    ):
            import re as _re
            path_match = _re.search(
                r'(?:in|on|inside|at|from)\s+([a-zA-Z]:[\\/][^\s]*|[a-zA-Z]\s+drive|desktop|documents|downloads)',
                tl
            )
            search_path = None
            if path_match:
                raw_path = path_match.group(1).strip()
                if raw_path.endswith("drive") and len(raw_path) > 5:
                    search_path = raw_path[0].upper() + ":\\"
                elif raw_path == "desktop":
                    search_path = os.path.join(os.path.expanduser("~"), "Desktop")
                elif raw_path == "documents":
                    search_path = os.path.join(os.path.expanduser("~"), "Documents")
                elif raw_path == "downloads":
                    search_path = os.path.join(os.path.expanduser("~"), "Downloads")
                else:
                    search_path = raw_path

            query = text
            for phrase in ["search for","find file","find folder","where is",
                           "locate","look for","search file","search folder",
                           "find the file","find the folder","search my","search"]:
                if phrase in tl:
                    idx = tl.find(phrase) + len(phrase)
                    query = text[idx:].strip()
                    if path_match:
                        query = query[:query.lower().find(path_match.group(0))].strip()
                    break
            query = query.strip(' .?"\' ') or text
            plan = {"tasks":[{"id":1,"action":"search_files",
                               "params":{"query": query, "search_path": search_path}}],
                    "summary":"search"}

        elif any(w in tl for w in [
                "create a python file", "create python file", "make a python file",
                "create a javascript file", "create javascript file", "make a js file",
                "create a html file", "create html file", "make a html file",
                "create a file", "make a file", "new file",
                "write a script", "create a script", "make a script",
                "create a program",
            ]):
            plan = {"tasks":[{"id":1,"action":"create_code_file",
                               "params":{"prompt": text}}],
                    "summary":"code_file"}

        elif any(w in tl for w in [
                "write code", "write a code", "code for",
                "write me a code", "give me code", "give me a code",
                "give me python", "give me a python",
                "give me javascript", "give me html",
                "show me code", "show me a code",
                "show me how to", "how do i code",
                "write me code", "generate code",
            ]):
            # Code in chat → lazy dev mode
            print(f"[STRIX] → Code in chat: dev (lazy mode)")
            plan = _task(text, "dev")

        # ── Priority 3: LLM ──────────────────────────────────
        else:
            model_key = _classify_llm(tl)
            print(f"[STRIX] → LLM model: {model_key}")
            plan = _task(text, model_key)

        # ── Execute ───────────────────────────────────────────
        if stream and plan:
            tasks = plan.get("tasks",[])
            if len(tasks) == 1 and tasks[0].get("action") == "llm_response":
                from brain.router import route_task
                gen = route_task(tasks[0], stream=True)
                def _save_stream(generator):
                    full = ""
                    for token in generator:
                        full += token
                        yield token
                    save_message("assistant", full)
                return _save_stream(gen)

        try:
            response = execute_plan(plan)
        except Exception as e:
            response = f"Error: {e}"
            print(f"[STRIX] Error: {e}")

        save_message("assistant", response)
        return response

    def get_history(self, limit=20):
        return get_recent_messages(limit=limit)

    def clear_memory(self):
        from memory.memory_db import clear_chat_history
        clear_chat_history()
        return "Memory cleared."


JarvisBrain = StrixBrain