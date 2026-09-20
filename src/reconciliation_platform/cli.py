"""Command-line entry point for the synthetic MVP."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from reconciliation_platform.pipeline import run_pipeline, summarize

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the financial reconciliation MVP.")
    parser.add_argument("--data-dir", default="data/synthetic/seed")
    args = parser.parse_args()
    result = run_pipeline(Path(args.data_dir))
    print(json.dumps(summarize(result), indent=2))
if __name__ == "__main__":
    main()
