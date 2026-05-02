# Final Submission Checklist

- `code.zip` contains the `code/` directory only.
- `support_tickets/output.csv` has been regenerated from the latest code.
- `~/hackerrank_orchestrate/log.txt` exists and contains the required transcript log.
- `python3 code/main.py` no-args smoke test regenerates `support_tickets/output.csv`.
- `python3 code/run_checks.py` passes.
- `python3 code/output_lint.py support_tickets/output.csv` passes.
- `python3 code/submission_report.py support_tickets/output.csv` passes.
- Sample parity is `10/10` for status, request_type, and product_area.
- Synthetic regression checks pass.
- `code/AGENT_CARD.md` is included for judge-facing agent documentation.
- `code/requirements.txt` is included and documents no third-party dependencies.
- `code.zip` does not include virtualenvs, `__pycache__`, `.pyc` files, `.DS_Store`, the `data/` corpus, or support ticket input CSVs.
- Final upload files:
  - `code.zip`
  - `support_tickets/output.csv`
  - `~/hackerrank_orchestrate/log.txt`
