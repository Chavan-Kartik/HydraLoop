import json
from pathlib import Path


def main() -> None:
    report = {
        "project": "HydraLoop",
        "status": "hello_pipeline_ok",
        "synthetic_only": True,
        "live_targeting": False,
        "message": "Governed pipeline skeleton is running.",
    }

    out = Path("reports/hello_pipeline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()