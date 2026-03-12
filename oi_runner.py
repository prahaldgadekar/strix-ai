"""
oi_runner.py — Open Interpreter integration for STRIX
Save as: E:\Strix\oi_runner.py

Install: pip install open-interpreter

Handles:
  - "create file X / write code for Y"   → creates file with code
  - Any complex task STRIX can't handle   → Open Interpreter fallback
"""

import os, re, subprocess, threading
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CODE_MODEL  = os.environ.get("CODING_MODEL",    "qwen2.5-coder:7b")

# ── File type defaults ────────────────────────────────────────
FILE_TEMPLATES = {
    ".py":   '# {name}\n\ndef main():\n    print("Hello from {name}")\n\nif __name__ == "__main__":\n    main()\n',
    ".js":   '// {name}\n\nfunction main() {{\n    console.log("Hello from {name}");\n}}\n\nmain();\n',
    ".html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <title>{name}</title>\n</head>\n<body>\n    <h1>{name}</h1>\n</body>\n</html>\n',
    ".css":  '/* {name} */\n\nbody {{\n    margin: 0;\n    font-family: Arial, sans-serif;\n}}\n',
    ".ts":   '// {name}\n\nfunction main(): void {{\n    console.log("Hello from {name}");\n}}\n\nmain();\n',
    ".java": 'public class {classname} {{\n    public static void main(String[] args) {{\n        System.out.println("Hello from {classname}");\n    }}\n}}\n',
    ".cpp":  '#include <iostream>\nusing namespace std;\n\nint main() {{\n    cout << "Hello from {name}" << endl;\n    return 0;\n}}\n',
    ".txt":  '# {name}\n',
    ".md":   '# {name}\n\n## Overview\n\nAdd description here.\n',
}

EXT_ALIASES = {
    "python":     ".py",
    "py":         ".py",
    "javascript": ".js",
    "js":         ".js",
    "html":       ".html",
    "webpage":    ".html",
    "css":        ".css",
    "typescript": ".ts",
    "ts":         ".ts",
    "java":       ".java",
    "cpp":        ".cpp",
    "c++":        ".cpp",
    "text":       ".txt",
    "txt":        ".txt",
    "markdown":   ".md",
    "md":         ".md",
}


def _get_oi():
    """Get Open Interpreter instance configured for Ollama."""
    try:
        import interpreter
        interpreter.llm.model          = f"ollama/{CODE_MODEL}"
        interpreter.llm.api_base       = OLLAMA_BASE
        interpreter.auto_run           = True      # no confirmation prompts
        interpreter.llm.context_window = 4096
        interpreter.llm.max_tokens     = 1000
        return interpreter
    except ImportError:
        return None


def create_file_with_code(prompt: str) -> str:
    """
    Parse prompt like:
      "create a python file called calculator and write add subtract functions"
      "create hello.py"
      "make a javascript file for a todo list"
    Then create the file — with code from OI if a task is described,
    or with boilerplate if just a file type was given.
    """
    prompt_lower = prompt.lower()

    # ── 1. Extract file extension ─────────────────────────────
    ext = None
    for alias, e in EXT_ALIASES.items():
        if alias in prompt_lower:
            ext = e
            break
    if not ext:
        ext = ".py"  # default to Python

    # ── 2. Extract filename ───────────────────────────────────
    # Look for patterns: "called X", "named X", "file X", "X.py"
    name = None

    # Explicit extension in prompt e.g. "hello.py"
    ext_match = re.search(r'\b([\w\-]+\.' + ext[1:] + r')\b', prompt_lower)
    if ext_match:
        name = ext_match.group(1)

    # "called X" or "named X"
    if not name:
        nm = re.search(r'(?:called|named|file|create|make)\s+([\w\-]+)', prompt_lower)
        if nm:
            candidate = nm.group(1)
            # skip generic words
            if candidate not in {"a", "an", "the", "file", "python", "javascript",
                                  "html", "css", "java", "cpp", "script", "code"}:
                name = candidate

    if not name:
        name = "new_file"

    # Ensure extension
    if not name.endswith(ext):
        name = name + ext

    # ── 3. Determine save location ────────────────────────────
    # Default: E:\ root (user's working drive)
    save_dir = "E:\\"
    if "desktop" in prompt_lower:
        save_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    elif "documents" in prompt_lower:
        save_dir = os.path.join(os.path.expanduser("~"), "Documents")
    elif re.search(r'[a-z]:\\', prompt_lower):
        path_m = re.search(r'([a-z]:\\[\w\\]*)', prompt_lower)
        if path_m:
            save_dir = path_m.group(1)

    filepath = os.path.join(save_dir, name)

    # ── 4. Decide: boilerplate or OI-generated code ───────────
    # If the prompt has a specific task beyond just "create file X"
    task_keywords = {
        "write", "code", "function", "class", "that", "which", "for",
        "implement", "build", "make it", "add", "with", "to", "do",
        "calculator", "login", "todo", "game", "sort", "fetch", "api",
        "scrape", "automate", "parse", "connect", "server", "crud",
    }
    has_task = sum(1 for w in task_keywords if w in prompt_lower) >= 2

    if has_task:
        code = _generate_code_with_oi(prompt, ext, name)
    else:
        # Just boilerplate
        template = FILE_TEMPLATES.get(ext, '# {name}\n')
        classname = name.replace(ext, "").replace("_", "").capitalize()
        code = template.format(name=name.replace(ext, ""), classname=classname)

    # ── 5. Write the file ─────────────────────────────────────
    try:
        os.makedirs(save_dir, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        # Open the file in VSCode or default editor
        try:
            subprocess.Popen(["code", filepath])
        except Exception:
            try:
                os.startfile(filepath)
            except Exception:
                pass

        return (
            f"✅ Created: {filepath}\n"
            f"📂 Location: {save_dir}\n"
            f"{'🤖 Code generated by AI' if has_task else '📝 Boilerplate template added'}\n"
            f"Opening in editor..."
        )

    except Exception as e:
        return f"❌ Couldn't create file: {e}"


def _generate_code_with_oi(prompt: str, ext: str, filename: str) -> str:
    """Use Open Interpreter / Ollama to write the actual code."""
    oi = _get_oi()

    if oi:
        try:
            lang_map = {".py": "Python", ".js": "JavaScript", ".html": "HTML",
                        ".css": "CSS", ".ts": "TypeScript", ".java": "Java",
                        ".cpp": "C++"}
            lang = lang_map.get(ext, "Python")

            code_prompt = (
                f"Write ONLY the {lang} code for this task. "
                f"No explanation, no markdown fences, just raw code:\n\n"
                f"Task: {prompt}\n"
                f"Filename: {filename}"
            )
            result = oi.chat(code_prompt)
            # Extract code from OI response
            if isinstance(result, list):
                for block in result:
                    if isinstance(block, dict) and block.get("type") == "code":
                        return block.get("content", "")
            return str(result)
        except Exception as e:
            print(f"[OI] Code gen failed: {e}, using Ollama direct")

    # Fallback — call Ollama directly (no OI needed)
    return _generate_code_ollama(prompt, ext, filename)


def _generate_code_ollama(prompt: str, ext: str, filename: str) -> str:
    """Direct Ollama call — no Open Interpreter needed."""
    try:
        import requests
        lang_map = {".py": "Python", ".js": "JavaScript", ".html": "HTML",
                    ".css": "CSS", ".ts": "TypeScript", ".java": "Java", ".cpp": "C++"}
        lang = lang_map.get(ext, "Python")

        response = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                "model":  CODE_MODEL,
                "prompt": (
                    f"Write ONLY the {lang} code for this task. "
                    f"Return raw code only, no markdown, no explanation.\n\n"
                    f"Task: {prompt}\nFilename: {filename}"
                ),
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 800}
            },
            timeout=30
        )
        raw = response.json().get("response", "")
        # Strip markdown code fences if model added them
        raw = re.sub(r"^```[\w]*\n?", "", raw.strip())
        raw = re.sub(r"\n?```$", "", raw.strip())
        return raw.strip()
    except Exception as e:
        print(f"[OI] Ollama direct call failed: {e}")
        # Last resort — return boilerplate
        template = FILE_TEMPLATES.get(ext, "# {name}\n")
        return template.format(name=filename.replace(ext, ""), classname="Main")


def run_oi_task(prompt: str) -> str:
    """
    General Open Interpreter fallback for complex tasks.
    Called when no STRIX action matches.
    """
    oi = _get_oi()
    if not oi:
        return (
            "Open Interpreter not installed, Boss. "
            "Run: pip install open-interpreter"
        )
    try:
        result = oi.chat(prompt)
        if isinstance(result, list):
            texts = [b.get("content","") for b in result if b.get("type") == "message"]
            return "\n".join(texts) or "Done, Boss."
        return str(result) or "Done, Boss."
    except Exception as e:
        return f"Open Interpreter error: {e}"


if __name__ == "__main__":
    # Quick test
    print(create_file_with_code("create a python file called calculator with add and subtract functions"))
