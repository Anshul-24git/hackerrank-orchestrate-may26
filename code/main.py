"""Command-line entry point for the deterministic support triage agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent import SupportTriageAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the support triage agent.")
    parser.add_argument(
        "--input",
        default="support_tickets/support_tickets.csv",
        help="Input support ticket CSV path. Defaults to support_tickets/support_tickets.csv.",
    )
    parser.add_argument(
        "--output",
        default="support_tickets/output.csv",
        help="Output prediction CSV path. Defaults to support_tickets/output.csv.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Support corpus directory. Defaults to <repo>/data.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = Path(args.data_dir) if args.data_dir else repo_root / "data"

    agent = SupportTriageAgent(data_dir=data_dir)
    predictions = agent.run_csv(Path(args.input), Path(args.output))
    print(
        f"Wrote {len(predictions)} predictions to {args.output} "
        f"using {agent.chunk_count} corpus chunks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
