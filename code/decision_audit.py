#!/usr/bin/env python3
"""Print a compact audit table for generated support triage output."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable, List


KNOWN_COMPANIES = ("HackerRank", "Claude", "Visa")
ALLOWED_STATUSES = {"replied", "escalated"}
ALLOWED_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}
RAW_METADATA_PATTERNS = (
    "title:",
    "description:",
    "last updated",
    "last modified",
    "cdn-cgi",
)
MARKDOWN_TABLE_PATTERNS = (
    "|----",
    "| ---",
    "---|",
    "<td",
    "<tr",
    "</td>",
    "</tr>",
)
RESPONSE_LIMIT = 900


def _shorten(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def audit_rows(rows: Iterable[dict[str, str]]) -> List[str]:
    issues: List[str] = []
    print(
        "row | company | subject | status | request_type | product_area | "
        "resp_len | just_len"
    )
    print("-" * 96)

    for index, row in enumerate(rows, start=1):
        company = (row.get("company") or "").strip()
        subject = row.get("subject") or ""
        status = (row.get("status") or "").strip().lower()
        request_type = (row.get("request_type") or "").strip()
        product_area = (row.get("product_area") or "").strip()
        response = row.get("response") or ""
        justification = row.get("justification") or ""
        combined = f"{response} {justification}"
        combined_lower = combined.lower()

        print(
            f"{index:02d} | {company or '(blank)'} | {_shorten(subject, 34)} | "
            f"{status or '(blank)'} | {request_type or '(blank)'} | "
            f"{product_area or '(blank)'} | {len(response)} | {len(justification)}"
        )

        if not response.strip():
            issues.append(f"row {index}: empty response")
        if not justification.strip():
            issues.append(f"row {index}: empty justification")
        if len(response) > RESPONSE_LIMIT:
            issues.append(f"row {index}: response too long ({len(response)} chars)")
        if status not in ALLOWED_STATUSES:
            issues.append(f"row {index}: invalid status {status!r}")
        if request_type not in ALLOWED_REQUEST_TYPES:
            issues.append(f"row {index}: invalid request_type {request_type!r}")

        for pattern in RAW_METADATA_PATTERNS:
            if pattern in combined_lower:
                issues.append(f"row {index}: raw metadata artifact '{pattern}'")

        for pattern in MARKDOWN_TABLE_PATTERNS:
            if pattern in combined_lower:
                issues.append(f"row {index}: markdown table artifact '{pattern}'")

        if company in KNOWN_COMPANIES:
            for other in KNOWN_COMPANIES:
                if other == company:
                    continue
                if re.search(rf"\b{re.escape(other)}\b", combined):
                    issues.append(f"row {index}: possible cross-company citation to {other}")

    return issues


def audit_file(path: Path) -> List[str]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return audit_rows(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit generated support triage output.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="support_tickets/output.csv",
        help="Generated output CSV path. Defaults to support_tickets/output.csv.",
    )
    args = parser.parse_args()

    issues = audit_file(Path(args.csv_path))
    if not issues:
        print("\nNo decision audit issues found.")
        return 0

    print("\nDecision audit issues:")
    for issue in issues:
        print("-", issue)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
