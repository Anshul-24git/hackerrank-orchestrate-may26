#!/usr/bin/env python3
"""Print a compact read-only report for a generated support triage CSV."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


REQUIRED_SCHEMA = [
    "issue",
    "subject",
    "company",
    "response",
    "product_area",
    "status",
    "request_type",
    "justification",
]
ALLOWED_STATUS = {"replied", "escalated"}
ALLOWED_REQUEST_TYPE = {"product_issue", "feature_request", "bug", "invalid"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize a generated support triage CSV.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="support_tickets/output.csv",
        help="Generated output CSV path. Defaults to support_tickets/output.csv.",
    )
    return parser


def average(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def print_counter(title: str, counter: Counter[str]) -> None:
    print(title)
    for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        label = key if key else "(blank)"
        print(f"- {label}: {value}")


def main() -> int:
    args = build_parser().parse_args()
    csv_path = Path(args.csv_path)

    if not csv_path.exists():
        raise SystemExit(f"Missing CSV: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    issues: list[str] = []
    if fieldnames != REQUIRED_SCHEMA:
        issues.append(f"schema mismatch: expected {REQUIRED_SCHEMA}, got {fieldnames}")

    company_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    request_type_counts: Counter[str] = Counter()
    product_area_counts: Counter[str] = Counter()
    response_lengths: list[int] = []
    justification_lengths: list[int] = []
    blank_product_rows: list[int] = []
    empty_response_rows: list[int] = []
    empty_justification_rows: list[int] = []
    invalid_status_rows: list[tuple[int, str]] = []
    invalid_request_type_rows: list[tuple[int, str]] = []

    for idx, row in enumerate(rows, start=1):
        company = (row.get("company") or "").strip()
        status = (row.get("status") or "").strip()
        request_type = (row.get("request_type") or "").strip()
        product_area = (row.get("product_area") or "").strip()
        response = (row.get("response") or "").strip()
        justification = (row.get("justification") or "").strip()

        company_counts[company] += 1
        status_counts[status] += 1
        request_type_counts[request_type] += 1
        product_area_counts[product_area] += 1
        response_lengths.append(len(response))
        justification_lengths.append(len(justification))

        if not product_area:
            blank_product_rows.append(idx)
        if not response:
            empty_response_rows.append(idx)
        if not justification:
            empty_justification_rows.append(idx)
        if status not in ALLOWED_STATUS:
            invalid_status_rows.append((idx, status))
        if request_type not in ALLOWED_REQUEST_TYPE:
            invalid_request_type_rows.append((idx, request_type))

    if empty_response_rows:
        issues.append(f"empty response rows: {empty_response_rows}")
    if empty_justification_rows:
        issues.append(f"empty justification rows: {empty_justification_rows}")
    if invalid_status_rows:
        issues.append(f"invalid status values: {invalid_status_rows}")
    if invalid_request_type_rows:
        issues.append(f"invalid request_type values: {invalid_request_type_rows}")

    print(f"Submission report for {csv_path}")
    print(f"total rows: {len(rows)}")
    print(f"average response length: {average(response_lengths):.1f}")
    print(f"average justification length: {average(justification_lengths):.1f}")
    print(f"escalated rows: {status_counts.get('escalated', 0)}")
    print(f"replied rows: {status_counts.get('replied', 0)}")
    print(f"invalid rows: {request_type_counts.get('invalid', 0)}")
    print(f"rows with blank product_area: {blank_product_rows or 'none'}")
    print(f"empty response rows: {empty_response_rows or 'none'}")
    print(f"empty justification rows: {empty_justification_rows or 'none'}")
    print(f"invalid status rows: {invalid_status_rows or 'none'}")
    print(f"invalid request_type rows: {invalid_request_type_rows or 'none'}")
    print()
    print_counter("count by company", company_counts)
    print()
    print_counter("count by status", status_counts)
    print()
    print_counter("count by request_type", request_type_counts)
    print()
    print_counter("count by product_area", product_area_counts)

    if issues:
        print()
        print("Report issues:")
        for issue in issues:
            print("-", issue)
        return 1

    print()
    print("Submission report checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
