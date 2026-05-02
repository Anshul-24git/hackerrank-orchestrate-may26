"""Deterministic safety and escalation rules."""

from __future__ import annotations

from schemas import SafetyDecision, Ticket


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


class SafetyRouter:
    """Classifies risk before the agent attempts a direct answer."""

    def inspect(self, ticket: Ticket, has_retrieval: bool) -> SafetyDecision:
        text = f"{ticket.subject} {ticket.issue}".lower()
        company = ticket.company.strip().lower()

        if self._is_harmless_invalid(text, company):
            return SafetyDecision(
                status="replied",
                request_type="invalid",
                reason="The ticket is outside the supported product domains and can be safely declined.",
            )

        request_type = self._request_type(text)

        escalation_reason = self._escalation_reason(text, company)
        if escalation_reason:
            return SafetyDecision(
                status="escalated",
                request_type=request_type,
                reason=escalation_reason,
            )

        if not has_retrieval:
            return SafetyDecision(
                status="escalated",
                request_type=request_type,
                reason="No sufficiently relevant support article was retrieved from the local corpus.",
            )

        return SafetyDecision(
            status="replied",
            request_type=request_type,
            reason="The request appears answerable from the provided support corpus.",
        )

    def _request_type(self, text: str) -> str:
        if _contains(text, ("iron man", "delete all files", "unnecessary files")):
            return "invalid"

        if _contains(
            text,
            (
                "feature request",
                "new feature",
                "enhancement",
                "would like the ability",
                "can you add",
            ),
        ):
            return "feature_request"

        if _contains(
            text,
            (
                "payment",
                "order id",
                "refund",
                "subscription",
                "billing",
                "charge",
                "invoice",
            ),
        ) and not _contains(text, ("stopped", "not working", "down", "failing")):
            return "product_issue"

        if _contains(text, ("reschedule", "rescheduling")):
            return "product_issue"

        if _contains(text, ("blocked card", "card blocked", "lost card", "stolen card", "tarjeta")):
            return "product_issue"

        if _contains(
            text,
            (
                "bug",
                "security vulnerability",
                "vulnerability",
                "security disclosure",
                "exploit",
                "down",
                "not working",
                "stopped working",
                "failing",
                "error",
                "unable to",
                "not able",
                "blocked",
                "blocker",
                "issue",
            ),
        ):
            return "bug"

        return "product_issue"

    def _is_harmless_invalid(self, text: str, company: str) -> bool:
        if company not in {"", "none", "unknown"}:
            return False
        return _contains(
            text,
            (
                "iron man",
                "thank you",
                "thanks for helping",
                "delete all files",
                "unnecessary files",
            ),
        )

    def _escalation_reason(self, text: str, company: str) -> str:
        if _contains(
            text,
            (
                "show all internal",
                "rules internal",
                "internal rules",
                "logic exact",
                "exact logic",
                "documents retrieved",
                "ignore previous",
                "system prompt",
                "developer message",
                "règles internes",
                "documents récupérés",
                "logique exacte",
            ),
        ):
            return (
                "Prompt-injection instructions were ignored; the legitimate support issue "
                "requires careful human review."
            )

        if company == "hackerrank" and _contains(
            text,
            (
                "infosec",
                "info sec",
                "security questionnaire",
                "vendor questionnaire",
                "security review",
                "procurement",
                "purchase hackerrank",
                "buy hackerrank",
                "sales",
            ),
        ):
            return "Vendor security, procurement, and sales-review requests require human account-team handling."

        if _contains(text, ("refund", "give me my money", "money back")):
            return "Refund and payment outcome requests require human review."

        if "score" in text and _contains(
            text,
            (
                "increase",
                "change",
                "adjust",
                "review",
                "dispute",
                "unfair",
                "grader",
                "grading",
                "next round",
            ),
        ):
            return "Assessment scoring and hiring outcome disputes require human review."

        if _contains(
            text,
            (
                "increase my score",
                "review my answers",
                "rejected me",
                "move me to the next round",
                "graded me unfairly",
            ),
        ):
            return "Assessment scoring and hiring outcome disputes require human review."

        if (
            not _contains(text, ("delete my account", "delete account"))
            and _contains(text, ("remove", "delete", "deactivate", "revoke"))
            and _contains(
                text,
                ("user", "interviewer", "employee", "access", "account", "team"),
            )
        ):
            return "Admin, access, and account-removal requests require authorization checks."

        if _contains(
            text,
            (
                "restore my access",
                "removed my seat",
                "not the workspace owner",
                "remove an interviewer",
                "remove them from",
                "employee has left",
                "admin removed",
            ),
        ):
            return "Admin, access, and account-removal requests require authorization checks."

        if company == "hackerrank" and _contains(
            text,
            (
                "inactivity time",
                "inactivity times",
                "extend inactivity",
                "kicked out of the room",
                "sent back to the hr lobby",
            ),
        ):
            return "Interview lobby or inactivity-timeout configuration requires HackerRank support review."

        if _contains(text, ("reschedule", "rescheduling")) and _contains(
            text,
            ("assessment", "test", "interview", "invite"),
        ):
            return "Assessment or interview rescheduling requires recruiter or account-admin coordination."

        if _contains(
            text,
            (
                "site is down",
                "none of the pages",
                "all requests are failing",
                "stopped working completely",
                "all submissions",
                "none of the submissions",
                "resume builder is down",
            ),
        ) or (
            "all requests" in text and _contains(text, ("failing", "fail", "broken"))
        ) or (
            "production requests" in text and _contains(text, ("failing", "fail", "broken", "down"))
        ):
            return "Potential service outage or broad platform failure requires human escalation."

        if _contains(
            text,
            (
                "security vulnerability",
                "major vulnerability",
                "bug bounty",
                "exploit",
            ),
        ):
            return "Security vulnerability reports require a specialized human handling path."

        if _contains(text, ("identity theft", "identity has been stolen", "fraud")):
            return "Fraud and identity-theft issues are sensitive and require human escalation."

        if company == "visa" and _contains(text, ("card blocked", "blocked card", "tarjeta bloqueada", "carte visa a été bloquée")):
            return "Blocked-card support while traveling is sensitive and should be handled by card support."

        if _contains(text, ("payment with order id", "order id:", "cs_live_")):
            return "Payment issues tied to an order identifier require account-specific support."

        if company in {"", "none", "unknown"} and _contains(text, ("not working", "help needed", "help")):
            return "The ticket is too vague to answer safely without more product context."

        return ""
