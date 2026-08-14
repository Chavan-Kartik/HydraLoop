import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC = REPO_ROOT / "src"

for p in (REPO_ROOT, SRC):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
