"""
strix/speech/tts.py — Text-to-Speech Subsystem Wrapper
======================================================
Wraps StrixTTS (Windows SAPI v5 + pyttsx3 fallback) with clean, thread-safe speech output.
Includes code-block stripping, sentence chunking, and mute control.
"""

from __future__ import annotations

from typing import Optional

try:
    from strix_tts import StrixTTS, tts_clean_speak
except ImportError:
    StrixTTS = None  # type: ignore
    tts_clean_speak = None  # type: ignore


class SpeechTTS:
    """
    Subsystem wrapper for STRIX Text-to-Speech.
    """

    def __init__(self):
        self._tts: Optional[StrixTTS] = None
        if StrixTTS:
            try:
                self._tts = StrixTTS()
                print("[STRIX SpeechTTS] Initialized")
            except Exception as e:
                print(f"[STRIX SpeechTTS] Error initializing TTS: {e}")

    @property
    def is_available(self) -> bool:
        return self._tts is not None and getattr(self._tts, "available", False)

    @property
    def is_muted(self) -> bool:
        return self._tts.muted if self._tts else True

    def speak(self, text: str, blocking: bool = False) -> None:
        """Clean markdown/code and queue text for spoken output."""
        if self._tts and text:
            self._tts.speak(text, blocking=blocking)

    def stop(self) -> None:
        """Stop current speech output immediately."""
        if self._tts:
            self._tts.stop()

    def toggle_mute(self) -> bool:
        """Toggle mute state and return new muted boolean."""
        if self._tts:
            return self._tts.toggle_mute()
        return True

    def clean_text(self, text: str) -> str:
        """Strip unreadable blocks, URLs, and code before speaking."""
        if tts_clean_speak:
            return tts_clean_speak(text)
        return text
