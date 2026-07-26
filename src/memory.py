"""
memory.py
Read and write the two memory files.
Static: goals, rules, schedule — edited by you manually, weekly cadence.
Dynamic: rolling log of your actual state — appended after every exchange.
"""

import os
from datetime import datetime, timedelta
from config import STATIC_MEMORY_PATH, DYNAMIC_MEMORY_PATH


def read_static() -> str:
    if not os.path.exists(STATIC_MEMORY_PATH):
        return "(no static memory file found)"
    with open(STATIC_MEMORY_PATH, "r") as f:
        return f.read().strip()


def read_dynamic() -> str:
    if not os.path.exists(DYNAMIC_MEMORY_PATH):
        return "(no entries yet)"
    with open(DYNAMIC_MEMORY_PATH, "r") as f:
        return f.read().strip()


def append_dynamic(line: str):
    """Append a single timestamped line to dynamic memory."""
    os.makedirs(os.path.dirname(DYNAMIC_MEMORY_PATH), exist_ok=True)
    with open(DYNAMIC_MEMORY_PATH, "a") as f:
        f.write(line + "\n")


def prune_dynamic(days: int = 3):
    """Remove entries older than `days` days. Called once at startup."""
    if not os.path.exists(DYNAMIC_MEMORY_PATH):
        return

    cutoff = datetime.now() - timedelta(days=days)

    with open(DYNAMIC_MEMORY_PATH, "r") as f:
        lines = f.readlines()

    kept = []
    for line in lines:
        # Lines start with [YYYY-MM-DD HH:MM]
        try:
            date_str = line[1:17]  # "2026-06-03 08:47"
            entry_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            if entry_date >= cutoff:
                kept.append(line)
        except (ValueError, IndexError):
            kept.append(line)  # keep malformed lines rather than delete

    with open(DYNAMIC_MEMORY_PATH, "w") as f:
        f.writelines(kept)
