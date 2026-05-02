# Approach

## Problem Framing

This solution is a deterministic terminal-based support triage agent for the HackerRank Orchestrate challenge. It handles support tickets across HackerRank, Claude, and Visa using only the local support corpus provided in the repository.

For each ticket, the agent classifies the request type, selects a product area, decides whether to reply or escalate, retrieves relevant documentation, and writes a grounded response to the required output CSV schema.

The core principle is conservative support automation: answer only when the corpus provides enough evidence, and escalate when the issue is high-risk, account-specific, sensitive, unsupported, or ambiguous.

## Architecture

- `main.py` exposes the CLI entry point.
- `agent.py` wires the ticket-processing pipeline together.
- `corpus_loader.py` loads and cleans markdown documents from the local corpus.
- `retriever.py` performs deterministic lexical retrieval over cleaned corpus chunks.
- `safety.py` applies invalid-ticket, prompt-injection, and escalation rules.
- `router.py` chooses status, request type, product area, response, and justification.
- `writer.py` reads input CSVs and writes the required output schema.
- `output_lint.py` validates generated outputs for citation and formatting issues.
- `decision_audit.py` prints a compact row-by-row audit table for generated outputs.
- `evidence_trace.py` supports auditability by showing the top same-company evidence behind decisions.
- `agent_trace.py` shows the full Observe -> Retrieve -> Assess -> Decide -> Act -> Verify loop for selected tickets.
- `run_checks.py` validates sample parity, synthetic regression cases, real output generation, and lint checks.
- `JUDGE_NOTES.md` provides a concise interview-ready explanation of the approach.

## Agentic Loop

This is a deterministic support triage agent, not a free-form chat agent. Its loop is explicit:

1. Observe: `writer.py` normalizes each ticket from CSV into a `Ticket`.
2. Retrieve: `corpus_loader.py` loads the local corpus and `retriever.py` ranks relevant same-company evidence.
3. Assess: `safety.py` checks invalid requests, prompt injection, sensitive actions, outages, fraud, security, score disputes, and account/admin risk.
4. Decide: `router.py` chooses `status`, `request_type`, and `product_area`.
5. Act: `router.py` generates the response and justification, and `writer.py` writes the output row.
6. Verify: `output_lint.py`, `decision_audit.py`, `evidence_trace.py`, and `run_checks.py` validate schema, safety, evidence quality, sample parity, and synthetic regressions.

## Retrieval Strategy

The retriever uses lexical token overlap with boosts for document title, path, category, and company/domain. This was chosen over external embeddings or LLM calls because the challenge rewards grounded, repeatable behavior over opaque generation.

Known-company tickets only cite evidence from the matching company corpus. If a ticket is from HackerRank, it cannot cite Visa or Claude documentation. If no strong same-company evidence exists, the agent suppresses weak citations and escalates when appropriate.

## Safety Strategy

The agent escalates issues involving:

- refunds, billing, payment disputes, or subscription actions
- score disputes or hiring outcome changes
- admin/account removals, access restoration, or permission changes
- broad outages or all-requests-failing reports
- fraud, identity theft, blocked cards, or sensitive financial issues
- security vulnerabilities or bug bounty reports
- vague "not working" issues without enough details
- unsupported or irreversible user requests

Prompt-injection text such as requests to reveal internal rules or ignore instructions is ignored. The legitimate support issue is still routed normally.

Invalid or out-of-scope tickets receive a short, safe response rather than a fabricated answer.

## Response Strategy

Responses are concise, support-agent style, and grounded in retrieved documentation. For normal replied tickets, the agent uses the strongest same-company evidence. For escalations, it focuses on the risk reason and human review path instead of forcing weak evidence into the answer.

The agent avoids unsupported policy claims and does not claim that a company can perform actions not supported by the corpus.

## Validation

Validation included:

- Running the labeled sample set and preserving 10/10 parity for status, request_type, and product_area.
- Running the real 29-ticket input and manually auditing high-risk rows.
- Adding `output_lint.py` to catch cross-company citations, raw metadata artifacts, empty responses, and overly long responses.
- Adding `decision_audit.py` and `evidence_trace.py` to make final decisions and evidence easier to inspect without changing outputs.
- Adding synthetic regression checks in `run_checks.py` for high-risk hidden-eval patterns such as score disputes, admin removal, Bedrock outages, prompt injection, and Visa card issues.
- Regenerating `support_tickets/output.csv` after final changes.

## Tradeoffs

This solution intentionally favors deterministic, explainable retrieval and routing over more complex semantic generation. Lexical retrieval can be less flexible than embeddings, but it is transparent, reproducible, and easier to defend in a support setting.

When evidence is weak, the agent escalates rather than guessing. This improves safety and reduces hallucinated support policies.
