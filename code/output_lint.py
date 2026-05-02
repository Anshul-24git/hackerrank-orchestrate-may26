"""Lightweight CSV output lint checks for judge-facing hygiene."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable, List


KNOWN_COMPANIES = ("HackerRank", "Claude", "Visa")
REQUIRED_COLUMNS = [
    "issue",
    "subject",
    "company",
    "response",
    "product_area",
    "status",
    "request_type",
    "justification",
]
ALLOWED_STATUSES = {"replied", "escalated"}
ALLOWED_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}
RAW_METADATA_PATTERNS = (
    "title:",
    "description:",
    "source_url",
    "final_url",
    "article_slug",
    "title_slug",
    "last updated",
    "last modified",
    "cdn-cgi",
    "breadcrumbs:",
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
WEAK_SOURCE_PATTERNS = (
    "glossary",
    "usage policy",
    "credit card rules",
    "centralized test settings",
    "automated security reviews",
    "changing the company name",
    "greenhouse",
    "interviewplanner",
)


def lint_rows(rows: Iterable[dict[str, str]]) -> List[str]:
    """Return human-readable lint issues for generated output rows."""
    issues: List[str] = []
    for index, row in enumerate(rows, start=1):
        company = (row.get("company") or "").strip()
        response = row.get("response") or ""
        justification = row.get("justification") or ""
        status = (row.get("status") or "").strip().lower()
        request_type = (row.get("request_type") or "").strip()
        combined = f"{response} {justification}"
        combined_lower = combined.lower()

        if status not in ALLOWED_STATUSES:
            issues.append(f"row {index}: invalid status {status!r}")
        if request_type not in ALLOWED_REQUEST_TYPES:
            issues.append(f"row {index}: invalid request_type {request_type!r}")
        if not response.strip():
            issues.append(f"row {index}: empty response")
        if not justification.strip():
            issues.append(f"row {index}: empty justification")
        if len(response) > 900:
            issues.append(f"row {index}: response too long ({len(response)} chars)")
        if len(justification) > 500:
            issues.append(f"row {index}: justification too long ({len(justification)} chars)")

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

        if status == "escalated" and "closest relevant support source" in combined_lower:
            for pattern in WEAK_SOURCE_PATTERNS:
                if pattern in combined_lower:
                    issues.append(f"row {index}: escalated response cites weak source '{pattern}'")

    return issues


def lint_file(path: Path) -> List[str]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_COLUMNS:
            return [
                "schema mismatch: expected "
                f"{REQUIRED_COLUMNS!r}, got {reader.fieldnames!r}"
            ]
        return lint_rows(reader)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint generated support triage CSV output.")
    parser.add_argument("csv_path", help="Generated output CSV path.")
    args = parser.parse_args()

    issues = lint_file(Path(args.csv_path))
    if not issues:
        print("No lint issues found.")
        return 0

    for issue in issues:
        print(issue)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
