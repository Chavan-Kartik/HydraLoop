"""Thin shim retained for backwards compatibility; delegates to the CLI."""

from hydraloop.cli import app

if __name__ == "__main__":
    app(["manifest"])
