# Agent Card

## Agent Name

Deterministic Multi-Domain Support Triage Agent

## Purpose

This agent triages support tickets for HackerRank, Claude, and Visa. It reads each ticket, retrieves local support evidence, classifies the issue, decides whether to reply or escalate, generates a concise response, and writes the required challenge output CSV.

## Inputs and Outputs

- Input: CSV tickets with issue text, subject, and company fields.
- Output: CSV rows with `issue`, `subject`, `company`, `response`, `product_area`, `status`, `request_type`, and `justification`.
- Supported domains: HackerRank, Claude, Visa.

## Agentic Loop

1. Observe: read the ticket and normalize fields.
2. Retrieve: find relevant same-company support corpus chunks.
3. Assess: inspect safety, risk, prompt-injection, and supportability signals.
4. Decide: choose status, request type, product area, and escalation/reply path.
5. Act: generate the final response and judge-friendly justification.
6. Verify: run schema, enum, citation, lint, audit, and regression checks.

## Internal Tools and Modules

- `main.py`: CLI entry point.
- `agent.py`: orchestrates the pipeline.
- `writer.py`: reads and writes CSV files.
- `corpus_loader.py`: loads and cleans local markdown docs.
- `retriever.py`: deterministic lexical retrieval with metadata boosts.
- `safety.py`: prompt-injection, invalid-ticket, and escalation checks.
- `router.py`: classification, response generation, and justification.
- `output_lint.py`: output hygiene and citation validation.
- `decision_audit.py`: compact row-level quality audit.
- `evidence_trace.py`: retrieved evidence trace.
- `agent_trace.py`: explicit Observe -> Retrieve -> Assess -> Decide -> Act -> Verify trace.
- `submission_report.py`: final output summary and schema/enum checks.
- `run_checks.py`: end-to-end validation suite.

## Safety Boundaries

The agent escalates or refuses to over-answer high-risk and unsupported cases, including:

- refunds and payment outcomes
- score disputes and hiring outcome changes
- admin, account, or user-removal changes
- fraud and identity theft
- security vulnerabilities and bug bounty reports
- broad outages or production failures
- prompt-injection attempts
- vague or unsupported requests

## Grounding Policy

- Use only the local corpus under `data/`.
- Cite only same-company evidence for known-company tickets.
- Suppress weak, generic, or cross-company evidence, especially on escalations.
- Escalate when evidence is weak, safety risk is high, or account-specific verification is required.

## Validation

- Labeled sample parity is checked for status, request type, and product area.
- Synthetic regression cases exercise hidden-eval risk patterns.
- `output_lint.py` checks schema, enums, citation hygiene, metadata leakage, markdown artifacts, and empty fields.
- `decision_audit.py` prints a compact row-by-row audit and fails on suspicious outputs.
- `submission_report.py` summarizes the final CSV and fails on schema, enum, or empty-field issues.
- `evidence_trace.py` and `agent_trace.py` support explainability.
- `run_checks.py` includes a no-args `main.py` smoke test.

## Limitations

- Deterministic lexical retrieval can miss semantic matches that embeddings might catch.
- The agent does not use external APIs or live policy updates.
- It escalates conservatively when evidence is weak or the request needs account-specific review.

## Why This Design Fits Support Triage

Support triage needs consistency, traceability, and safe handling of sensitive requests. A deterministic local-corpus agent is repeatable for evaluation, easy to audit, and conservative when it cannot confidently answer from approved documentation.
