# Judge Notes

## 30-Second Explanation

This solution is a deterministic support triage agent for HackerRank, Claude, and Visa tickets. It reads tickets from CSV, retrieves relevant evidence from the local support corpus, classifies the ticket, decides whether to reply or escalate, and writes the required output schema. The system is intentionally conservative: it answers routine corpus-backed questions and escalates high-risk, sensitive, account-specific, vague, or unsupported requests.

## Architecture Summary

- `main.py`: CLI entry point.
- `agent.py`: end-to-end orchestration.
- `corpus_loader.py`: loads and cleans local markdown corpus files.
- `retriever.py`: deterministic lexical retrieval with metadata boosts.
- `safety.py`: invalid-ticket, prompt-injection, and escalation rules.
- `router.py`: product area, status, request type, response, and justification.
- `writer.py`: input/output CSV handling.
- `output_lint.py`: output hygiene checks.
- `run_checks.py`: sample parity, synthetic regression, real generation, and lint validation.

## Why This Is an Agent

It is a deterministic support triage agent with an explicit Observe -> Retrieve -> Assess -> Decide -> Act -> Verify loop. It is not a free-form chat agent: it observes tickets, retrieves local evidence, assesses safety/risk, decides classification and routing, acts by producing the response row, and verifies outputs through linting and regression checks. `agent_trace.py` demonstrates this loop for any ticket row.

## Why Deterministic Lexical Retrieval

The challenge rewards grounded support behavior. I chose deterministic lexical retrieval instead of external LLM calls because it is repeatable, inspectable, fast, and uses only the provided corpus. That makes the output easier to defend in a judge interview: every response is tied to local evidence or a clear escalation rule.

## Same-Company Evidence Filtering

Known-company tickets can only cite that company's corpus. HackerRank tickets cite HackerRank evidence, Claude tickets cite Claude evidence, and Visa tickets cite Visa evidence. If the ticket company is blank, evidence is used only when the domain is strongly inferred; otherwise the agent avoids citations and escalates or declines safely.

## Safety Escalation

The agent escalates refunds, score or hiring-outcome disputes, admin or account-removal requests, broad outages, security vulnerabilities, fraud, identity theft, blocked cards, vague "not working" reports, and unsupported sensitive cases. Escalation responses focus on the risk reason and the correct review team rather than forcing weak evidence into the answer.

## Prompt Injection

Prompt-injection text such as requests to reveal internal rules, developer messages, system prompts, or retrieved documents is ignored. The agent still routes the legitimate support issue, and the justification mentions that prompt-injection instructions were ignored.

## Validation

`output_lint.py` checks required schema, allowed status and request type values, cross-company citations, raw metadata leakage, empty fields, long responses, and markdown table artifacts. `decision_audit.py` prints a compact row-by-row quality audit. `evidence_trace.py` shows the top same-company evidence behind decisions, which is useful if a judge asks how responses are grounded. `run_checks.py` regenerates the sample output, verifies labeled sample parity, runs synthetic regression tickets for hidden-eval risks, regenerates the real output, and runs the quality gates.

If asked about grounding, I would point to same-company evidence filtering, output linting, decision auditing, and the `evidence_trace.py` helper.

If asked what makes this feel like a shipped agent, I would point to `AGENT_CARD.md` for the system-card summary, `run_checks.py` for repeatable validation, `output_lint.py` and `decision_audit.py` for quality gates, `evidence_trace.py` and `agent_trace.py` for explainability, and `submission_report.py` for final output reporting.

## Hidden-Eval Risks Found and Fixed

Manual and synthetic testing found several risks: score-change wording that did not use the exact sample phrase, third-party user-removal/admin requests that looked answerable, Bedrock production outages that could be answered with support docs instead of escalated, and prompt-injection requests being routed to a Visa-specific team for non-Visa tickets. These were fixed with general safety rules while preserving sample parity.

## Tradeoffs and Future Improvements

The main tradeoff is that lexical retrieval can miss semantic matches that embeddings might catch. I accepted that because deterministic behavior and source traceability are valuable in this challenge. With more time, I would add a small curated synonym map per product area, richer test fixtures, and a confidence report that explains why each escalation or reply was chosen.
