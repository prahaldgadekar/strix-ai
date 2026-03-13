"""
brain/executor.py — STRIX v4.0
================================
Executes multi-step task plans.
Handles all actions including new path-based file/folder creation.
"""

import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from brain.router import route_task
from memory.memory_db import save_task


def execute_plan(plan: dict) -> str:
    tasks   = plan.get("tasks", [])
    summary = plan.get("summary", "")

    if not tasks:
        return "No tasks to execute."

    results = []

    for task in tasks:
        task_id = task.get("id", "?")
        action  = task.get("action", "unknown")
        desc    = task.get("description", "")
        params  = task.get("params", {})

        print(f"[Executor] Step {task_id}: {action} — {desc}")

        try:
            # Handle new path-based actions directly here
            if action == "create_folder_path":
                result = _create_folder_path(params)

            elif action == "create_file_at_path":
                result = _create_file_at_path(params)

            elif action == "create_file_in_folder":
                result = _create_file_in_folder(params)

            else:
                # All other actions go through router
                result = route_task(task)

            save_task(f"{action}: {desc}", "success", str(result)[:200])

        except Exception as e:
            result = f"Step {task_id} failed: {e}"
            save_task(f"{action}: {desc}", "error", str(e))
            print(f"[Executor] Step {task_id} error: {e}")

        results.append((desc or action, result))

    # Format response
    if len(results) == 1:
        return results[0][1]

    # Multi-step — summarize all results
    lines = []
    all_ok = True
    for label, res in results:
        ok = "failed" not in str(res).lower() and "error" not in str(res).lower()
        if not ok:
            all_ok = False
        icon = "✓" if ok else "✗"
        lines.append(f"{icon} {res}")

    if all_ok:
        lines.insert(0, f"All {len(results)} steps done, Boss.")
    else:
        lines.insert(0, f"Completed {len(results)} steps (check errors above).")

    return "\n".join(lines)


# ── Path-based file/folder handlers ──────────────────────────

def _create_folder_path(params: dict) -> str:
    path = params.get("path", "")
    if not path:
        return "No path specified."
    try:
        os.makedirs(path, exist_ok=True)
        name = os.path.basename(path.rstrip("\\/"))
        return f"Folder '{name}' created at {os.path.dirname(path)}."
    except PermissionError:
        return f"Permission denied creating folder at {path}. Try running as Admin."
    except Exception as e:
        return f"Could not create folder: {e}"


def _create_file_at_path(params: dict) -> str:
    path    = params.get("path", "")
    content = params.get("content", "")
    if not path:
        return "No file path specified."
    try:
        parent = os.path.dirname(path)
        # Only makedirs if parent is a real non-root directory that doesn't exist
        if parent and parent != path and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        name = os.path.basename(path)
        return f"File '{name}' created at {parent or path}."
    except PermissionError:
        return f"Permission denied creating file at {path}. Try running STRIX as Admin."
    except Exception as e:
        return f"Could not create file: {e}"


def _create_file_in_folder(params: dict) -> str:
    folder   = params.get("folder", "")
    filename = params.get("filename", "file.txt")
    content  = params.get("content", "")
    try:
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{filename}' created inside '{os.path.basename(folder)}'."
    except Exception as e:
        return f"Could not create file: {e}"