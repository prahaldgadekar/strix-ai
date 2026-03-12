"""
strix.py  (was jarvis.py)
--------------------------
STRIX Main Entry Point.

Usage:
    python strix.py          → Launch full GUI
    python strix.py --cli    → Command line mode
    python strix.py --check  → Check system status and dependencies
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def check_dependencies():
    print("\n" + "="*55)
    print("  STRIX — Dependency Check")
    print("="*55)

    checks = {
        "PySide6":           "PySide6",
        "SpeechRecognition": "speech_recognition",
        "pyttsx3":           "pyttsx3",
        "TextBlob":          "textblob",
        "requests":          "requests",
        "psutil":            "psutil",
        "pyautogui":         "pyautogui",
        "python-dotenv":     "dotenv",
    }

    all_ok = True
    for name, module in checks.items():
        try:
            __import__(module)
            print(f"  OK  {name}")
        except ImportError:
            print(f"  !!  {name}  <- pip install {name.lower()}")
            all_ok = False

    print()
    try:
        import requests as req
        resp = req.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in resp.json().get("models", [])]
        print(f"  OK  Ollama running  | Models: {', '.join(models) if models else 'none pulled yet'}")
        if not models:
            print("      -> Pull: ollama pull phi3")
            print("      -> Pull: ollama pull qwen2.5-coder")
    except Exception:
        print("  !!  Ollama not running -> start: ollama serve")
        print("      Then: ollama pull phi3")

    print()
    if os.path.exists(".env"):
        print("  OK  .env file found")
    else:
        print("  !!  No .env file -> copy .env.example and add API keys")

    print("="*55)
    if all_ok:
        print("  All packages OK. STRIX is ready.")
    else:
        print("  Install missing packages, then run again.")
    print("="*55 + "\n")


def run_cli():
    print("\n" + "="*50)
    print("  STRIX — CLI Mode  (type 'exit' to quit)")
    print("="*50 + "\n")

    from brain.core import StrixBrain
    brain = StrixBrain()

    while True:
        try:
            user_input = input("YOU: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[STRIX] Goodbye Boss.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "bye"}:
            print("[STRIX] Goodbye Boss!")
            break

        response = brain.process(user_input)
        print(f"\nSTRIX: {response}\n")


def run_gui():
    from strix_gui import run_gui as _run
    _run()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--check" in args:
        check_dependencies()
    elif "--cli" in args:
        run_cli()
    else:
        run_gui()