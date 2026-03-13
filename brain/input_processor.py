"""
brain/input_processor.py — STRIX v4.3
=======================================
Voice recognition: Google Speech en-IN only.
  - Single API call per phrase (fast)
  - en-IN handles Indian accent + Hinglish commands correctly
  - Devanagari results filtered out (can't match commands)
  - No TextBlob spell correction (corrupts Hindi/Marathi words)
"""

# ── Devanagari → Latin command map ────────────────────────────
# When Google occasionally returns script characters, convert them
DEVA_FIX = {
    "प्ले":    "play",
    "खोलो":   "open",
    "बंद करो": "close",
    "बजाओ":   "play",
    "दिखाओ":  "show",
    "बताओ":   "tell me",
    "रोको":   "stop",
    "रुको":   "stop",
    "अगला":   "next",
    "पिछला":  "previous",
    "उघड":    "open",
    "वाजव":   "play",
    "थांबव":  "stop",
    "दाखव":   "show",
    "सांग":   "tell me",
}


def _fix_devanagari(text: str) -> str:
    for deva, latin in DEVA_FIX.items():
        text = text.replace(deva, latin)
    return text.strip()


# ── Text processing ───────────────────────────────────────────

def process_text_input(text: str) -> dict:
    """Classify input. No spell correction — corrupts Hinglish."""
    return {
        "original":  text,
        "corrected": text,
        "intent":    _classify_intent(text),
    }


def _classify_intent(text: str) -> str:
    tl = text.lower()
    if any(w in tl for w in ["weather", "temperature", "rain", "forecast",
                               "barish", "mausam", "paus", "hava"]):
        return "weather"
    if any(w in tl for w in ["news", "headline", "latest",
                               "khabar", "batmya", "baatmya"]):
        return "news"
    if any(w in tl for w in ["code", "program", "function", "script", "class"]):
        return "code"
    if any(w in tl for w in ["joke", "funny", "laugh", "mazak"]):
        return "joke"
    if any(w in tl for w in ["hello", "hi", "hey", "how are you",
                               "namaste", "namaskar", "kasa ahe"]):
        return "greeting"
    if any(w in tl for w in ["play", "music", "song", "bajao", "gaana",
                               "vaajav", "gana lav"]):
        return "music"
    return "general"


# ── Voice Input ───────────────────────────────────────────────

class VoiceInput:
    """
    Microphone input. Google Speech en-IN only.

    en-IN correctly recognises:
      - English commands ("open chrome", "play music")
      - Hinglish ("bajao gaana", "kholo youtube")
      - Indian pronunciation ("play pal pal dil ke paas")

    Multi-language chains (mr-IN / hi) are REMOVED — they return
    Devanagari script like "प्ले" which can't match command prefixes.
    """

    def __init__(self):
        self._available = False
        self._sr = None
        self._r  = None
        try:
            import speech_recognition as sr
            self._sr = sr
            self._r  = sr.Recognizer()
            self._r.energy_threshold         = 300
            self._r.dynamic_energy_threshold  = True
            self._r.pause_threshold           = 2.5
            self._r.non_speaking_duration     = 2.0
            self._r.phrase_threshold          = 0.3
            self._r.operation_timeout         = None
            self._available = True
            print("[VoiceInput] Mode: Google Speech (en-IN)")
        except ImportError:
            print("[VoiceInput] speech_recognition not installed")

    def listen_once(self, timeout: int = 8, phrase_limit: int = 20) -> str:
        """Listen for one command. Returns lowercase text or ''."""
        if not self._available:
            return ""
        try:
            with self._sr.Microphone() as src:
                self._r.adjust_for_ambient_noise(src, duration=0.3)
                print("[VoiceInput] Listening (Google)...")
                audio = self._r.listen(src, timeout=timeout,
                                        phrase_time_limit=phrase_limit)

            # Single en-IN call — handles Indian accent + Hinglish
            text = self._r.recognize_google(audio, language="en-IN")
            text = text.strip().lower()

            # Fix any Devanagari that slipped through
            text = _fix_devanagari(text)

            if text:
                print(f"[VoiceInput] en-IN: {text}")
            return text

        except self._sr.WaitTimeoutError:
            return ""
        except self._sr.UnknownValueError:
            return ""
        except self._sr.RequestError as e:
            print(f"[VoiceInput] Google API error: {e}")
            return ""
        except Exception as e:
            print(f"[VoiceInput] Error: {e}")
            return ""

    @property
    def available(self) -> bool:
        return self._available