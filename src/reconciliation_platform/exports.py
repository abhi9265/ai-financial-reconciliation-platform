"""Export helpers for reconciliation results."""
from __future__ import annotations

import csv
import io
import json
from typing import Iterable


def results_csv(rows: Iterable[dict]) -> str:
    rows = list(rows)
    fields = ["result_id","record_id","candidate_record_id","status","match_tier","confidence","explanation","amount_difference","created_at"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def report_json(report: dict) -> str:
    return json.dumps(report, indent=2, default=str, sort_keys=True)
