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
    - Keeps news, info, answers fully intact
    - Converts symbols to words where needed
    - NO character cap — speaks everything readable
    """
    # ── Remove code blocks — never read raw code ─────────────
    text = re.sub(r'```[\s\S]*?```', 'Code block here.', text)
    text = re.sub(r'`[^`]*`', '', text)

    # ── Remove markdown headers but keep the text ─────────────
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # ── Speak symbols as words ────────────────────────────────
    symbol_words = [
        ('!=',  'not equal to'),
        ('==',  'equals'),
        ('>=',  'greater than or equal to'),
        ('<=',  'less than or equal to'),
        ('->',  'arrow'),
        ('=>',  'returns'),
        ('//',  ''),            # strip comments
        ('/**', ''),
        ('/*',  ''),
        ('*/',  ''),
        ('...',  '.'),
    ]
    for sym, word in symbol_words:
        text = text.replace(sym, f' {word} ' if word else ' ')

    # ── Remove remaining symbols silently ─────────────────────
    remove_symbols = ['*', '#', '_', '`', '\\', '|', '^', '~',
                      '@', '[', ']', '{', '}', '<', '>', '+',
                      '=', '%', '$', '&']
    for sym in remove_symbols:
        text = text.replace(sym, ' ')

    # ── Punctuation fixes ──────────────────────────────────────
    text = text.replace(';', '.')
    text = text.replace(':', '. ')
    # Slash between words → "slash"
    text = re.sub(r'(\w)/(\w)', r'\1 slash \2', text)
    text = text.replace('/', ' ')

    # ── Filter line by line ────────────────────────────────────
    lines = text.split('\n')
    good_lines = []
    for line in lines:
        if not _should_skip_line(line):
            good_lines.append(line.strip())

    text = ' '.join(good_lines)

    # ── Clean up whitespace ────────────────────────────────────
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip()

    # ── NO hard cap — return full cleaned text ─────────────────
    return text


def _split_sentences(text: str) -> list:
    """
    Split into natural sentence chunks for fluent delivery.
    Each chunk max 300 chars — long enough to sound natural,
    short enough to start speaking quickly.
    """
    # Split on sentence endings
    parts = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for p in parts:
        if len(current) + len(p) < 300:
            current += (" " if current else "") + p
        else:
            if current:
                chunks.append(current.strip())
            current = p
    if current:
        chunks.append(current.strip())

    # Filter out any empty or skip-worthy chunks
    return [c for c in chunks if c.strip() and not _should_skip_line(c)] or [text[:300]]


class StrixTTS:
    def __init__(self):
        self.muted     = False
        self.available = False
        self._queue    = queue.Queue()
        self._engine   = None
        self._mode     = None

        # Try Windows SAPI first — zero latency
        try:
            import win32com.client
            self._sapi = win32com.client.Dispatch("SAPI.SpVoice")
            self._configure_sapi()
            self._mode = "sapi"
            self.available = True
            print("[TTS] Using Windows SAPI — full response mode.")
        except Exception:
            self._sapi = None

        # Fallback to pyttsx3
        if not self.available:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._configure_pyttsx3()
                self._mode = "pyttsx3"
                self.available = True
                print("[TTS] Using pyttsx3 fallback.")
            except Exception as e:
                print(f"[TTS] Not available: {e}")
                return

        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def _configure_sapi(self):
        try:
            voices = self._sapi.GetVoices()
            for i in range(voices.Count):
                name = voices.Item(i).GetDescription().lower()
                if "david" in name or "mark" in name or "george" in name:
                    self._sapi.Voice = voices.Item(i)
                    break
            self._sapi.Rate   = -1    # slightly slower = clearer
            self._sapi.Volume = 100
        except Exception:
            pass

    def _configure_pyttsx3(self):
        try:
            voices = self._engine.getProperty("voices")
            for v in voices:
                if "david" in v.name.lower() or "george" in v.name.lower():
                    self._engine.setProperty("voice", v.id)
                    break
        except Exception:
            pass
        self._engine.setProperty("rate",   158)
        self._engine.setProperty("volume", 1.0)

    def _worker(self):
        """Drain queue — speaks one sentence chunk at a time."""
        while True:
            try:
                text = self._queue.get(timeout=0.5)
                if text is None:
                    break
                if not self.muted and text.strip():
                    try:
                        if self._mode == "sapi":
                            self._sapi.Speak(text, 0)
                        else:
                            self._engine.say(text)
                            self._engine.runAndWait()
                    except Exception as e:
                        print(f"[TTS] Speak error: {e}")
                        if self._mode == "pyttsx3":
                            try:
                                import pyttsx3
                                self._engine = pyttsx3.init()
                                self._configure_pyttsx3()
                            except Exception:
                                pass
                self._queue.task_done()
            except queue.Empty:
                continue

    def speak(self, text: str, blocking: bool = False):
        """
        Clean and queue full text for speaking.
        No cap — speaks everything readable.
        """
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
                self._sapi.Speak("", 2)   # SVSFPurgeBeforeSpeak = 2
            else:
                self._engine.stop()
        except Exception:
            pass

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self.muted:
            self.stop()
        return self.muted


JarvisTTS = StrixTTS