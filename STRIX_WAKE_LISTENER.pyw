"""
brain/input_processor.py — STRIX v4.1
========================================
UPGRADE: Voice now handles Hindi + English mixed commands.
  - Tries "hi" (Hindi) recognition first, then "en-IN" fallback
  - Uses show_all=True so Google returns multiple transcription candidates
  - TextBlob spell-correction disabled for Hinglish (it corrupts Hindi words)
  - Tuned thresholds for Indian accent / background noise
"""

import re


# ── Text processing ───────────────────────────────────────────

def process_text_input(text: str) -> dict:
    """Classify input text. Spell-correction skipped for voice (Hinglish-safe)."""
    intent = _classify_intent(text)
    return {
        "original":  text,
        "corrected": text,   # No spell-correction — it corrupts Hindi words
        "intent":    intent,
    }


def _classify_intent(text: str) -> str:
    """Simple rule-based intent classification."""
    tl = text.lower()
    if any(w in tl for w in ["weather", "temperature", "rain", "forecast", "barish", "mausam"]):
        return "weather"
    if any(w in tl for w in ["news", "headline", "latest", "khabar", "khabren"]):
        return "news"
    if any(w in tl for w in ["code", "program", "function", "script", "class"]):
        return "code"
    if any(w in tl for w in ["joke", "funny", "laugh", "mazak", "hasao"]):
        return "joke"
    if any(w in tl for w in ["hello", "hi", "hey", "how are you", "kaise", "namaste"]):
        return "greeting"
    if any(w in tl for w in ["play", "bajao", "song", "gaana", "music"]):
        return "music"
    return "general"


# ── Voice Input ───────────────────────────────────────────────

class VoiceInput:
    """
    Microphone input — handles Hindi + English mixed commands.

    How it works:
      1. Primary attempt: language="hi" — catches Hindi words + numbers
      2. Fallback: language="en-IN" — catches English with Indian accent
      3. show_all=True — Google returns all transcription candidates
         so we pick the best one (the one with most known keywords)

    Key timing settings:
      pause_threshold      = 2.5  → waits 2.5s of silence before stopping
      non_speaking_duration = 2.0  → buffer before speech starts
      phrase_time_limit    = 20   → max 20 seconds per command
      energy_threshold     = 300  → mic sensitivity
    """

    def __init__(self):
        self._available = False
        try:
            import speech_recognition as sr
            self._sr = sr
            self._r  = sr.Recognizer()

            # Tuned for Indian accent / mixed language
            self._r.energy_threshold         = 300
            self._r.dynamic_energy_threshold  = True
            self._r.pause_threshold           = 2.5
            self._r.non_speaking_duration     = 2.0
            self._r.phrase_threshold          = 0.3
            self._r.operation_timeout         = None

            self._available = True
        except ImportError:
            print("[Voice] speech_recognition not installed")

    def listen_once(self, timeout: int = 8, phrase_limit: int = 20) -> str:
        """
        Listen for one voice command.
        Tries Hindi recognition first, then English-Indian fallback.
        """
        if not self._available:
            return ""
        try:
            with self._sr.Microphone() as src:
                self._r.adjust_for_ambient_noise(src, duration=0.3)
                print("[Voice] Listening…")
                audio = self._r.listen(
                    src,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )

            # ── Attempt 1: Hindi (hi) — best for Hinglish / numbers ──
            try:
                result = self._r.recognize_google(
                    audio,
                    language="hi",
                    show_all=False
                )
                text = result.strip() if isinstance(result, str) else ""
                if text:
                    print(f"[Voice] Hindi result: {text}")
                    # If result is all Hindi script (Devanagari), it's not a
                    # command — fall through to English attempt
                    if _is_devanagari_only(text):
                        print("[Voice] Pure Hindi script — trying English fallback")
                    else:
                        return text
            except Exception:
                pass

            # ── Attempt 2: English-Indian accent ─────────────────────
            try:
                result = self._r.recognize_google(
                    audio,
                    language="en-IN",
                    show_all=False
                )
                text = result.strip() if isinstance(result, str) else ""
                if text:
                    print(f"[Voice] English-IN result: {text}")
                    return text
            except Exception:
                pass

            # ── Attempt 3: show_all — pick best candidate ─────────────
            try:
                all_results = self._r.recognize_google(
                    audio,
                    language="en-IN",
                    show_all=True
                )
                best = _pick_best_candidate(all_results)
                if best:
                    print(f"[Voice] Best candidate: {best}")
                    return best
            except Exception:
                pass

            return ""

        except self._sr.WaitTimeoutError:
            return ""
        except self._sr.UnknownValueError:
            return ""
        except self._sr.RequestError as e:
            print(f"[Voice] API error: {e}")
            return ""
        except Exception as e:
            print(f"[Voice] Error: {e}")
            return ""

    @property
    def available(self) -> bool:
        return self._available


# ── Helpers ───────────────────────────────────────────────────

def _is_devanagari_only(text: str) -> bool:
    """True if text is only Devanagari script (pure Hindi, not Hinglish)."""
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    return latin_chars == 0 and len(text) > 0


# Keywords that indicate a valid command (English or Hinglish)
_COMMAND_KEYWORDS = {
    "open", "play", "start", "show", "close", "stop", "pause",
    "search", "find", "create", "make", "tell", "what", "how",
    "weather", "news", "system", "code", "write", "help",
    "bajao", "kholo", "band", "chalu", "dikhao", "batao",
    "gaana", "music", "song", "chrome", "spotify", "youtube",
}

def _pick_best_candidate(all_results) -> str:
    """
    From Google's show_all results, pick the transcript with
    the most known command keywords.
    """
    if not all_results:
        return ""

    # all_results is a dict with 'alternative' list
    if isinstance(all_results, dict):
        alternatives = all_results.get("alternative", [])
    else:
        return ""

    if not alternatives:
        return ""

    best_text  = ""
    best_score = -1

    for alt in alternatives:
        transcript = alt.get("transcript", "").strip()
        confidence = alt.get("confidence", 0.0)
        if not transcript:
            continue

        tl = transcript.lower()
        keyword_hits = sum(1 for kw in _COMMAND_KEYWORDS if kw in tl)

        # Score = keyword hits * 2 + confidence bonus
        score = keyword_hits * 2 + confidence
        if score > best_score:
            best_score = score
            best_text  = transcript

    return best_text