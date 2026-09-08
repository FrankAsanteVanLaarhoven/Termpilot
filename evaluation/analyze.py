#!/usr/bin/env python3
"""Summarise evaluation CSV. Prints placeholders when no pilot rows exist."""

from __future__ import annotations

import csv
from pathlib import Path

PATH = Path(__file__).with_name("schema.csv")


def main() -> None:
    rows = list(csv.DictReader(PATH.read_text(encoding="utf-8").splitlines()))
    data = [r for r in rows if r.get("participant_code")]
    if not data:
        print("No pilot results recorded. Demo and system-test results are shown separately.")
        return
    times = [float(r["planning_time_minutes"]) for r in data if r["planning_time_minutes"]]
    print(f"n={len(data)} median_planning_time={sorted(times)[len(times)//2] if times else 'n/a'}")


if __name__ == "__main__":
    main()
