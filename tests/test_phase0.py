from pathlib import Path


REQUIRED_FILES = [
    "README.md",
    "SAFETY.md",
    "ASSUMPTIONS.md",
    "LIMITATIONS.md",
    "DATA_CARD.md",
    "MODEL_CARD.md",
    "requirements.txt",
    ".gitignore",
    "configs/hydraloop.yaml",
    "configs/experiments/demo.yaml",
    "scripts/write_run_manifest.py",
    "scripts/hello_pipeline.py",
]


def test_required_files_exist():
    for file_path in REQUIRED_FILES:
        assert Path(file_path).exists(), f"Missing required file: {file_path}"


def test_reports_folder_exists():
    assert Path("reports").exists()


def test_safety_file_contains_synthetic_only():
    content = Path("SAFETY.md").read_text(encoding="utf-8")
    assert "synthetic" in content.lower()


def test_assumptions_register_has_entries():
    content = Path("ASSUMPTIONS.md").read_text(encoding="utf-8")
    assert "A01" in content
    assert "A10" in content