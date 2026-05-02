#!/usr/bin/env python3
"""Print a compact evidence trace for support triage decisions."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent import SupportTriageAgent
from writer import read_tickets


STRONG_EVIDENCE_SCORE = 3.0


def _shorten(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trace retrieved evidence behind triage decisions.")
    parser.add_argument(
        "--input",
        default="support_tickets/support_tickets.csv",
        help="Input support ticket CSV path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of tickets to trace.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = repo_root / input_path

    agent = SupportTriageAgent(data_dir=repo_root / "data")
    tickets = read_tickets(input_path)
    if args.limit is not None:
        tickets = tickets[: max(args.limit, 0)]

    print(
        "row | company | subject | status | request_type | product_area | "
        "evidence_company | evidence_category | evidence | score | note"
    )
    print("-" * 132)

    for index, ticket in enumerate(tickets, start=1):
        raw_hits = agent.retriever.search(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            limit=12,
        )
        same_domain_hits = agent.router._filter_evidence_for_ticket(ticket, raw_hits)
        has_strong_evidence = bool(
            same_domain_hits and same_domain_hits[0].score >= STRONG_EVIDENCE_SCORE
        )
        safety = agent.router.safety.inspect(ticket, has_retrieval=has_strong_evidence)
        prediction = agent.predict(ticket)

        if same_domain_hits:
            top = same_domain_hits[0]
            evidence_company = top.chunk.company
            evidence_category = top.chunk.category
            evidence_title = agent.router._clean_title(top.chunk.title) or top.chunk.path
            evidence_score = f"{top.score:.1f}"
        else:
            evidence_company = "-"
            evidence_category = "-"
            evidence_title = "no same-company evidence"
            evidence_score = "-"

        if safety.status == "escalated":
            note = f"safety escalation: {safety.reason}"
        elif not has_strong_evidence:
            note = "no strong same-company evidence"
        else:
            note = "strong same-company evidence"

        print(
            f"{index:02d} | "
            f"{ticket.company or '(blank)'} | "
            f"{_shorten(ticket.subject, 28)} | "
            f"{prediction.status} | "
            f"{prediction.request_type} | "
            f"{prediction.product_area or '(blank)'} | "
            f"{evidence_company} | "
            f"{evidence_category} | "
            f"{_shorten(evidence_title, 38)} | "
            f"{evidence_score} | "
            f"{_shorten(note, 52)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
