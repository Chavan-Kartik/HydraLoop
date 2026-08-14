"""Fail CI if forbidden authorship markers or emoji appear in tracked sources.

This is a hard gate for a human hackathon submission: no AI-tool attribution,
no co-author trailers, no emoji in code or docs.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PHRASES = [
    "cursor",
    "claude",
    "copilot",
    "chatgpt",
    "co-authored-by",
    "as an ai",
    "large language model wrote",
]

SCAN_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".ts", ".tsx", ".js", ".jsx", ".css"}
SKIP_DIRS = {".git", ".venv", "node_modules", ".next", "__pycache__", ".pytest_cache"}

# Emoji and pictographic ranges; excludes ordinary punctuation and symbols.
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF\U00002B00-\U00002BFF]"
)

# Legitimate self-references to the check itself must not trip it.
ALLOWLIST_PATHS = {"scripts/check_authenticity.py"}


def _tracked_files() -> list[Path]:
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT).decode("utf-8")
        files = [REPO_ROOT / line for line in out.splitlines() if line.strip()]
    except Exception:
        files = [p for p in REPO_ROOT.rglob("*") if p.is_file()]
    result = []
    for p in files:
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in SCAN_SUFFIXES:
            result.append(p)
    return result


def scan() -> list[str]:
    problems: list[str] = []
    for path in _tracked_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWLIST_PATHS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        lower = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lower:
                problems.append(f"{rel}: forbidden phrase '{phrase}'")
        if EMOJI_RE.search(text):
            problems.append(f"{rel}: emoji character detected")
    return problems


def main() -> int:
    problems = scan()
    if problems:
        print("Authenticity check FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Authenticity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
