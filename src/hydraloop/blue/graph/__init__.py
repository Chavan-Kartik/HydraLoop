"""Point-in-time graph snapshots and a hand-rolled GraphSAGE aggregator."""

from .snapshot import GraphSnapshot, build_snapshot

__all__ = ["GraphSnapshot", "build_snapshot"]
