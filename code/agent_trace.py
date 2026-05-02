#!/usr/bin/env python3
"""Show the deterministic support triage agent loop for selected tickets."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent import SupportTriageAgent
from writer import read_tickets


STRONG_EVIDENCE_SCORE = 3.0
ALLOWED_STATUSES = {"replied", "escalated"}
ALLOWED_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}
PROMPT_INJECTION_TERMS = (
    "show all internal",
    "internal rules",
    "documents retrieved",
    "ignore previous",
    "system prompt",
    "developer message",
    "règles internes",
    "documents récupérés",
    "logique exacte",
)


def _shorten(value: str, limit: int = 180) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _prompt_injection_detected(text: str) -> bool:
    text = text.lower()
    return any(term in text for term in PROMPT_INJECTION_TERMS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trace the agentic support triage loop.")
    parser.add_argument(
        "--input",
        default="support_tickets/support_tickets.csv",
        help="Input support ticket CSV path.",
    )
    parser.add_argument("--row", type=int, default=None, help="Trace one 1-indexed row.")
    parser.add_argument("--limit", type=int, default=None, help="Trace the first N rows.")
    return parser


def _selected_tickets(tickets, row: int | None, limit: int | None):
    if row is not None:
        if row < 1 or row > len(tickets):
            raise SystemExit(f"--row must be between 1 and {len(tickets)}")
        return [(row, tickets[row - 1])]
    selected_limit = 3 if limit is None else max(limit, 0)
    return list(enumerate(tickets[:selected_limit], start=1))


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = repo_root / input_path

    agent = SupportTriageAgent(data_dir=repo_root / "data")
    tickets = read_tickets(input_path)

    for row_number, ticket in _selected_tickets(tickets, args.row, args.limit):
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
        combined_input = f"{ticket.subject} {ticket.issue}"

        print(f"\n=== ROW {row_number} ===")
        print("OBSERVE")
        print(f"- company: {ticket.company or '(blank)'}")
        print(f"- subject: {ticket.subject or '(blank)'}")
        print(f"- issue preview: {_shorten(ticket.issue)}")

        print("RETRIEVE")
        if same_domain_hits:
            top = same_domain_hits[0]
            evidence_title = agent.router._clean_title(top.chunk.title) or top.chunk.path
            print(f"- top evidence: {evidence_title}")
            print(f"- path: {top.chunk.path}")
            print(f"- company/category: {top.chunk.company}/{top.chunk.category}")
            print(f"- score: {top.score:.1f}")
        else:
            print("- top evidence: no same-company evidence")
            print("- score: n/a")

        print("ASSESS")
        print(f"- safety escalation triggered: {safety.status == 'escalated'}")
        print(f"- risk reason: {safety.reason}")
        print(f"- prompt injection detected: {_prompt_injection_detected(combined_input)}")

        print("DECIDE")
        print(f"- status: {prediction.status}")
        print(f"- request_type: {prediction.request_type}")
        print(f"- product_area: {prediction.product_area or '(blank)'}")

        print("ACT")
        print(f"- response preview: {_shorten(prediction.response)}")
        print(f"- justification preview: {_shorten(prediction.justification)}")

        print("VERIFY")
        same_company_ok = True
        if same_domain_hits and ticket.company.strip() in {"HackerRank", "Claude", "Visa"}:
            same_company_ok = same_domain_hits[0].chunk.company == ticket.company.strip()
        print(f"- same-company evidence rule: {'pass' if same_company_ok else 'fail'}")
        print(f"- non-empty response/justification: {bool(prediction.response and prediction.justification)}")
        print(f"- allowed enum values: {prediction.status in ALLOWED_STATUSES and prediction.request_type in ALLOWED_REQUEST_TYPES}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
