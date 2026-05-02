"""CSV reading and writing helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List

from schemas import OUTPUT_COLUMNS, Prediction, Ticket


def _get(row: dict[str, str], *names: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lowered:
            return (lowered[name.lower()] or "").strip()
    return ""


def read_tickets(path: Path) -> List[Ticket]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [
            Ticket(
                issue=_get(row, "issue"),
                subject=_get(row, "subject"),
                company=_get(row, "company"),
                raw=dict(row),
            )
            for row in reader
        ]


def write_predictions(path: Path, predictions: Iterable[Prediction]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for prediction in predictions:
            writer.writerow(prediction.as_row())
