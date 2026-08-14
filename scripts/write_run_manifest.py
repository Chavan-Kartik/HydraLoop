import json
import hashlib
import subprocess
import sys
import platform
from datetime import datetime, timezone
from pathlib import Path


def get_git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("utf-8")
            .strip()
        )
    except Exception:
        return "unknown"


def get_config_hash(config_path: str) -> str:
    path = Path(config_path)
    if not path.exists():
        return "missing-config"
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def main() -> None:
    config_path = "configs/hydraloop.yaml"
    manifest = {
        "project": "HydraLoop",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "git_sha": get_git_sha(),
        "config_path": config_path,
        "config_hash": get_config_hash(config_path),
        "synthetic_only": True,
        "live_targeting": False,
        "content_generation": False,
    }

    out = Path("reports/run_manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    print(f"Run manifest written to {out}")


if __name__ == "__main__":
    main()