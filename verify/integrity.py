"""SHA-256 of sim/, verify/ and data/ before and after a run (PLAN.md 3.6 step 3).

The agent has no tool that writes outside proposals/, so any change here means tampering.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHED = ["sim", "verify", "data"]
SKIP_DIRS = {"__pycache__"}


def digest() -> dict[str, str]:
    out = {}
    for top in WATCHED:
        for p in sorted((ROOT / top).rglob("*")):
            if p.is_file() and not SKIP_DIRS & set(p.parts):
                out[str(p.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def changed(before: dict[str, str], after: dict[str, str] | None = None) -> list[str]:
    after = digest() if after is None else after
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
