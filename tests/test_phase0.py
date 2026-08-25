from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "docs/RESPONSIBLE_AI.md",
    "docs/ASSUMPTIONS.md",
    "docs/LIMITATIONS.md",
    "docs/DATA_CARD.md",
    "docs/MODEL_CARD.md",
    "requirements.txt",
    "pyproject.toml",
    "Makefile",
    "make.ps1",
    "Dockerfile",
    ".gitignore",
    "configs/hydraloop.yaml",
    "configs/experiments/demo.yaml",
    "src/hydraloop/__init__.py",
    "src/hydraloop/cli.py",
]


def test_required_files_exist():
    for file_path in REQUIRED_FILES:
        assert (REPO / file_path).exists(), f"Missing required file: {file_path}"


def test_safety_file_contains_abstraction_policy():
    content = (REPO / "docs" / "RESPONSIBLE_AI.md").read_text(encoding="utf-8").lower()
    assert "synthetic" in content
    assert "abstraction policy" in content


def test_assumptions_register_has_entries():
    content = (REPO / "docs" / "ASSUMPTIONS.md").read_text(encoding="utf-8")
    assert "A01" in content
    assert "A10" in content


def test_manifest_writer_emits_json(tmp_path):
    from hydraloop.config import load_config
    from hydraloop.manifest import write_manifest

    cfg = load_config()
    out = write_manifest(tmp_path, cfg, "run_test")
    assert out.exists()
    import json

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["project"] == "HydraLoop"
    assert data["safety"]["synthetic_only"] is True
    assert data["config_hash"]
