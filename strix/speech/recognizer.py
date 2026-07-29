"""
strix/speech/recognizer.py — Speech Recognition & Wake-Word Subsystem
=======================================================================
Wraps speech recognition listening and wake word detection for STRIX voice mode.
Includes Hinglish fallback, noise floor calibration, and self-hearing guards.
"""

from __future__ import annotations

from typing import Callable, Optional

try:
    from brain.input_processor import VoiceInput
except ImportError:
    VoiceInput = None  # type: ignore


class SpeechRecognizer:
    """
    Subsystem wrapper for STRIX Speech Recognition & Wake Word listening.
    """

    def __init__(self):
        self._voice_input = None
        if VoiceInput:
            try:
                self._voice_input = VoiceInput()
                print("[STRIX SpeechRecognizer] Initialized")
            except Exception as e:
                print(f"[STRIX SpeechRecognizer] Error initializing VoiceInput: {e}")

    @property
    def is_available(self) -> bool:
        return self._voice_input is not None and getattr(self._voice_input, "available", False)

    def listen_once(self, timeout: int = 8, phrase_limit: int = 20) -> str:
        """
        Listen for one spoken command (Hindi + English).
        Returns recognized transcript or empty string.
        """
        if self._voice_input and self._voice_input.available:
            return self._voice_input.listen_once(timeout=timeout, phrase_limit=phrase_limit)
        return ""
