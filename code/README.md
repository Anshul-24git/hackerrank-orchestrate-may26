# Support Triage Agent

This is the final deterministic support triage agent for the HackerRank Orchestrate challenge.

The agent reads support tickets from CSV, retrieves relevant guidance from the local `data/` corpus, classifies each ticket, generates a concise support response, and writes the required output CSV schema. It uses only the Python standard library and never calls external APIs.

`requirements.txt` is intentionally empty of packages because the solution has no third-party dependencies.

## Run

Run the real challenge tickets with safe defaults:

```bash
python3 code/main.py
```

This defaults to `support_tickets/support_tickets.csv` -> `support_tickets/output.csv`.

Run the sample tickets from the repository root:

```bash
python3 code/main.py --input support_tickets/sample_support_tickets.csv --output support_tickets/sample_output.csv
```

Run the real challenge tickets:

```bash
python3 code/main.py --input support_tickets/support_tickets.csv --output support_tickets/output.csv
```

Lint generated output for citation and formatting issues:

```bash
python3 code/output_lint.py support_tickets/output.csv
```

Print a compact row-by-row decision audit:

```bash
python3 code/decision_audit.py support_tickets/output.csv
```

Print the final submission summary:

```bash
python3 code/submission_report.py support_tickets/output.csv
```

Trace the top same-company evidence behind decisions:

```bash
python3 code/evidence_trace.py --input support_tickets/support_tickets.csv --limit 5
```

Show the explicit Observe -> Retrieve -> Assess -> Decide -> Act -> Verify loop:

```bash
python3 code/agent_trace.py --input support_tickets/support_tickets.csv --limit 3
```

Run the full local validation suite:

```bash
python3 code/run_checks.py
```

## Design

- `corpus_loader.py` loads and cleans markdown files from `data/hackerrank`, `data/claude`, and `data/visa`.
- `retriever.py` ranks chunks using lexical token overlap plus title, path, category, and company boosts.
- `safety.py` applies deterministic invalid-ticket, safety, and escalation rules.
- `router.py` chooses product area, status, request type, response text, and justification from safety decisions plus retrieved evidence.
- `writer.py` reads input CSVs and writes predictions using the required output schema.
- `output_lint.py` checks generated CSVs for cross-company citations, raw metadata artifacts, and overly long responses.
- `decision_audit.py` prints row-level output lengths and flags suspicious decisions.
- `submission_report.py` prints final row counts, averages, distribution summaries, and schema/enum checks.
- `evidence_trace.py` prints a compact read-only trace of final decisions and top same-company evidence.
- `agent_trace.py` demonstrates the explicit deterministic agent loop for judge/debug explanation.
- `run_checks.py` regenerates sample output, verifies sample parity, runs synthetic regression checks, regenerates real output, runs output linting, runs the decision audit, and prints the submission report.
- `agent.py` wires the pipeline together.
- `main.py` exposes the CLI, with no-argument defaults for the real challenge input and output paths.
- `AGENT_CARD.md` documents purpose, boundaries, grounding, validation, and limitations.
- `JUDGE_NOTES.md` summarizes the approach for judge interview/readability.
- `FINAL_CHECKLIST.md` lists final submission artifacts and validation checks.
- `requirements.txt` documents that the solution uses only the Python standard library.

## Safety Philosophy

- Use only the provided local corpus as support evidence.
- Keep retrieval and routing deterministic for repeatable evaluation.
- Escalate high-risk, account-specific, payment/refund, security, outage, fraud, score-dispute, admin, vague, or unsupported requests.
- Cite only same-company evidence for known-company tickets; suppress weak or unrelated evidence on escalations.
- Ignore prompt-injection text and route the legitimate support issue instead.
- Keep responses concise, practical, and grounded in the retrieved corpus.

## Output Schema

Output columns are exactly:

```csv
issue,subject,company,response,product_area,status,request_type,justification
```

## Final Validation

To regenerate outputs, compare the labeled sample decisions, run synthetic regression checks, run output linting, run the decision audit, and print the submission report in one command:

```bash
python3 code/run_checks.py
```
