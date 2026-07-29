"""
strix_tts.py — STRIX v4.0
============================
Fixes:
  • No character cap — speaks the full response
  • Smart content filter — skips code blocks, URLs, symbols
  • Speaks news/info fully sentence by sentence
  • Chunk size increased to 300 chars for natural flow
  • Skips lines that are clearly unreadable (pure symbols, URLs, paths)
"""

import threading
import queue
import re


# ── What to skip entirely ─────────────────────────────────────
def _should_skip_line(line: str) -> bool:
    """Return True if this line should NOT be spoken."""
    s = line.strip()
    if not s:
        return True
    # Pure symbols / separators
    if re.match(r'^[\-=_\*\#\~\^\.\/\\|]{3,}$', s):
        return True
    # URLs
    if re.match(r'https?://', s):
        return True
    # File paths like E:\Strix\file.py
    if re.match(r'^[A-Za-z]:\\', s):
        return True
    # Pure numbers / timestamps like "22:31:01"
    if re.match(r'^[\d\:\.\,\s]+$', s):
        return True
    # Very short meaningless tokens
    if len(s) < 3:
        return True
    return False


def tts_clean_speak(text: str) -> str:
    """
    Convert response text to clean speakable version.
    - Removes code blocks entirely
    - If output is big (>220 chars or multi-paragraph), speaks title/summary & stops
    - Converts symbols to words where needed
    """
    if not text or not text.strip():
        return ""

    raw_text = text.strip()

    # ── Remove code blocks — never read raw code ─────────────
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]*`', '', text)

    # ── If output is big, extract title / first sentence only ─
    is_big_output = len(raw_text) > 220 or '\n\n' in raw_text or '```' in raw_text

    # ── Remove markdown headers but keep the text ─────────────
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # ── Unit and symbol pronunciations ────────────────────────
    # Temperature (24.7C -> 24.7 degrees Celsius, 76F -> 76 degrees Fahrenheit)
    text = re.sub(r'(\d+(?:\.\d+)?)\s*°?\s*C\b', r'\1 degrees Celsius', text)
    text = re.sub(r'(\d+(?:\.\d+)?)\s*°?\s*F\b', r'\1 degrees Fahrenheit', text)
    text = text.replace('°', ' degrees ')

    # Speed & Data units
    unit_replacements = [
        (r'\bkm/s\b', 'kilometers per second'),
        (r'\bkm/h\b', 'kilometers per hour'),
        (r'\bm/s\b', 'meters per second'),
        (r'\bmph\b', 'miles per hour'),
        (r'\bMB/s\b', 'megabytes per second'),
        (r'\bGB/s\b', 'gigabytes per second'),
        (r'\bKB/s\b', 'kilobytes per second'),
        (r'\bMbps\b', 'megabits per second'),
        (r'\bGbps\b', 'gigabits per second'),
        (r'\bKbps\b', 'kilobits per second'),
        (r'\bMB\b', 'megabytes'),
        (r'\bGB\b', 'gigabytes'),
        (r'\bKB\b', 'kilobytes'),
        (r'\bTB\b', 'terabytes'),
        ('%', ' percent '),
    ]
    for pattern, repl in unit_replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    # ── Speak symbols as words ────────────────────────────────
    symbol_words = [
        ('!=',  'not equal to'),
        ('==',  'equals'),
        ('>=',  'greater than or equal to'),
        ('<=',  'less than or equal to'),
        ('->',  'arrow'),
        ('=>',  'returns'),
        ('//',  ''),
        ('...',  '.'),
    ]
    for sym, word in symbol_words:
        text = text.replace(sym, f' {word} ' if word else ' ')

    # ── Remove remaining symbols silently ─────────────────────
    remove_symbols = ['*', '#', '_', '`', '\\', '|', '^', '~',
                      '@', '[', ']', '{', '}', '<', '>', '+',
                      '=', '$', '&']
    for sym in remove_symbols:
        text = text.replace(sym, ' ')

    text = text.replace(';', '.')
    text = text.replace(':', '. ')
    text = re.sub(r'(\w)/(\w)', r'\1 slash \2', text)
    text = text.replace('/', ' ')

    lines = text.split('\n')
    good_lines = []
    for line in lines:
        if not _should_skip_line(line):
            good_lines.append(line.strip())

    text = ' '.join(good_lines)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()

    # If output is big, speak title / summary line only and stop
    if is_big_output and text:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        title_summary = ""
        for s in sentences:
            if len(title_summary) + len(s) <= 160:
                title_summary += (" " if title_summary else "") + s
            else:
                break
        if not title_summary:
            title_summary = sentences[0][:150]
        return f"{title_summary.strip()} Details are on screen, Boss."

    return text


def _split_sentences(text: str) -> list:
    """
    Split into natural sentence chunks for fluent delivery.
    """
    parts = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for p in parts:
        if len(current) + len(p) < 250:
            current += (" " if current else "") + p
        else:
            if current:
                chunks.append(current.strip())
            current = p
    if current:
        chunks.append(current.strip())

    return [c for c in chunks if c.strip() and not _should_skip_line(c)] or [text[:250]]


class StrixTTS:
    def __init__(self):
        self.muted     = False
        self.available = False
        self._queue    = queue.Queue()
        self._engine   = None
        self._mode     = "sapi"

        # Test SAPI availability
        try:
            import win32com.client
            _test_sapi = win32com.client.Dispatch("SAPI.SpVoice")
            self.available = True
            print("[TTS] Using Windows SAPI — full response mode.")
        except Exception:
            self._mode = "pyttsx3"

        # Fallback to pyttsx3 test
        if not self.available:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._configure_pyttsx3()
                self.available = True
                print("[TTS] Using pyttsx3 fallback.")
            except Exception as e:
                print(f"[TTS] Not available: {e}")
                return

        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def _configure_sapi_instance(self, sapi):
        try:
            voices = sapi.GetVoices()
            selected = False
            for pref in ["zira", "hazel", "helen", "catherine", "susan", "linda", "aria", "eva", "female", "woman"]:
                for i in range(voices.Count):
                    name = voices.Item(i).GetDescription().lower()
                    if pref in name:
                        sapi.Voice = voices.Item(i)
                        selected = True
                        print(f"[TTS] Selected Female Voice: {voices.Item(i).GetDescription()}")
                        break
                if selected:
                    break
            sapi.Rate   = 0     # Clear, natural pacing
            sapi.Volume = 100
        except Exception:
            pass

    def _configure_pyttsx3(self):
        try:
            voices = self._engine.getProperty("voices")
            for v in voices:
                vname = v.name.lower()
                if any(m in vname for m in ["zira", "hazel", "helen", "catherine", "female", "woman", "her"]):
                    self._engine.setProperty("voice", v.id)
                    print(f"[TTS] Selected Female Voice (pyttsx3): {v.name}")
                    break
        except Exception:
            pass
        self._engine.setProperty("rate",   158)
        self._engine.setProperty("volume", 1.0)

    def _worker(self):
        """Drain queue — speaks one sentence chunk at a time with thread-safe COM init."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        sapi = None
        if self._mode == "sapi":
            try:
                import win32com.client
                sapi = win32com.client.Dispatch("SAPI.SpVoice")
                self._configure_sapi_instance(sapi)
            except Exception as e:
                print(f"[TTS] SAPI dispatch error: {e}")

        while True:
            try:
                text = self._queue.get(timeout=0.5)
                if text is None:
                    break
                if not self.muted and text.strip():
                    try:
                        if sapi:
                            sapi.Speak(text, 0)
                        elif self._mode == "pyttsx3" and self._engine:
                            self._engine.say(text)
                            self._engine.runAndWait()
                    except Exception as e:
                        print(f"[TTS] Speak error: {e}")
                self._queue.task_done()
            except queue.Empty:
                continue

        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass

    def speak(self, text: str, blocking: bool = False):
        if not self.available or self.muted or not text.strip():
            return
        cleaned = tts_clean_speak(text)
        if not cleaned.strip():
            return
        chunks = _split_sentences(cleaned)
        for chunk in chunks:
            if chunk.strip():
                self._queue.put(chunk)

    def stop(self):
        """Clear queue and stop speech immediately."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception:
                pass
        try:
            if self._mode == "sapi":
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    import win32com.client
                    s = win32com.client.Dispatch("SAPI.SpVoice")
                    s.Speak("", 2)   # SVSFPurgeBeforeSpeak = 2
                except Exception:
                    pass
            elif self._engine:
                self._engine.stop()
        except Exception:
            pass

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self.muted:
            self.stop()
        return self.muted


JarvisTTS = StrixTTS