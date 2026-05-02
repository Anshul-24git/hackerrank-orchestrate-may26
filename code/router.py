"""Ticket classification, routing, and response generation."""

from __future__ import annotations

import re
from typing import List

from retriever import LexicalRetriever, tokenize
from safety import SafetyRouter
from schemas import Prediction, RetrievedChunk, SafetyDecision, Ticket


class TicketRouter:
    """Combines retrieval evidence with deterministic routing rules."""

    def __init__(self, retriever: LexicalRetriever, safety: SafetyRouter | None = None) -> None:
        self.retriever = retriever
        self.safety = safety or SafetyRouter()

    def route(self, ticket: Ticket) -> Prediction:
        raw_retrieved = self.retriever.search(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            limit=12,
        )
        retrieved = self._filter_evidence_for_ticket(ticket, raw_retrieved)
        has_retrieval = bool(retrieved and retrieved[0].score >= 3.0)
        safety = self.safety.inspect(ticket, has_retrieval=has_retrieval)
        product_area = self._product_area(ticket, retrieved, safety.status, safety.request_type)

        if safety.request_type == "invalid" and safety.status != "escalated":
            response = self._invalid_response()
        elif safety.status == "escalated":
            response = self._escalation_response(ticket, safety.reason, retrieved)
        else:
            response = self._grounded_response(ticket, retrieved)

        justification = self._justification(safety, retrieved)

        return Prediction(
            issue=ticket.issue,
            subject=ticket.subject,
            company=ticket.company,
            response=response,
            product_area=product_area,
            status=safety.status,
            request_type=safety.request_type,
            justification=justification,
        )

    def _filter_evidence_for_ticket(
        self,
        ticket: Ticket,
        retrieved: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """Keep cited evidence inside the ticket's domain."""
        company = ticket.company.strip().lower()
        if company in {"hackerrank", "claude", "visa"}:
            return [hit for hit in retrieved if hit.chunk.company.lower() == company]

        inferred = self._infer_strong_domain(ticket)
        if inferred:
            return [hit for hit in retrieved if hit.chunk.company.lower() == inferred]
        return []

    def _infer_strong_domain(self, ticket: Ticket) -> str:
        text = f"{ticket.subject} {ticket.issue}".lower()
        domain_terms = {
            "hackerrank": ("hackerrank", "assessment", "coding test", "mock interview"),
            "claude": ("claude", "anthropic", "bedrock", "lti"),
            "visa": ("visa", "card issuer", "credit card", "debit card"),
        }
        matches = [
            company
            for company, terms in domain_terms.items()
            if any(term in text for term in terms)
        ]
        return matches[0] if len(matches) == 1 else ""

    def _product_area(
        self,
        ticket: Ticket,
        retrieved: List[RetrievedChunk],
        status: str,
        request_type: str,
    ) -> str:
        text = f"{ticket.subject} {ticket.issue}".lower()
        company = ticket.company.strip().lower()

        if request_type == "invalid":
            if "thank" in text:
                return ""
            if company in {"", "none", "unknown"}:
                return "conversation_management"

        if status == "escalated" and company in {"", "none", "unknown"}:
            return ""

        if company == "visa":
            if "lost" in text and "stolen" in text and "card" in text:
                return "general_support"
            if any(term in text for term in ("minimum", "rules", "fee", "surcharge", "us virgin islands")):
                return "rules_and_fees"
            if any(
                term in text
                for term in (
                    "traveller",
                    "traveler",
                    "travel",
                    "cash",
                    "card blocked",
                    "blocked card",
                    "voyage",
                    "viaje",
                    "tarjeta",
                    "bloqueada",
                    "carte",
                )
            ):
                return "travel_support"
            if any(term in text for term in ("dispute", "charge", "merchant", "wrong product")):
                return "dispute_resolution"
            if any(term in text for term in ("fraud", "identity")):
                return "fraud_protection"

        if company == "claude":
            if "bedrock" in text:
                return "amazon_bedrock"
            if any(term in text for term in ("lti", "students", "education", "professor", "university", "canvas", "lms")):
                return "claude_for_education"
            if any(term in text for term in ("vulnerability", "bug bounty", "safety", "security disclosure")):
                return "safeguards"
            if any(term in text for term in ("team", "workspace", "seat", "admin", "remove")):
                return "admin_management"
            if any(term in text for term in ("crawl", "privacy", "data", "conversation")):
                return "privacy"

        if company == "hackerrank":
            if "infosec" in text or "security questionnaire" in text or "vendor questionnaire" in text:
                return "general_help"
            community_hint = any(
                term in text
                for term in ("apply tab", "certificate", "certification", "profile name", "mock interview", "resume")
            )
            community_hint = community_hint or ("practice" in text and "best practice" not in text)
            if community_hint:
                return "community"
            if any(term in text for term in ("interviewer", "employee", "user", "team", "subscription")):
                return "settings"
            if any(term in text for term in ("assessment", "test", "candidate", "score", "submissions", "compatib", "zoom")):
                return "screen"

        if retrieved:
            return retrieved[0].chunk.category
        return ""

    def _invalid_response(self) -> str:
        return (
            "I can help with HackerRank, Claude, and Visa support questions. "
            "This request is outside that scope, so there is no support action for me to take."
        )

    def _escalation_response(self, ticket: Ticket, reason: str, retrieved: List[RetrievedChunk]) -> str:
        team = self._escalation_team(ticket, reason)
        response = (
            f"I am escalating this to the {team}. {reason} "
            "A human reviewer should verify the account, policy, or incident details before any action is taken."
        )
        if retrieved and self._strong_escalation_source(ticket, reason, retrieved[0]):
            response += f" The closest relevant support source is \"{self._clean_title(retrieved[0].chunk.title)}.\""
        return response

    def _grounded_response(self, ticket: Ticket, retrieved: List[RetrievedChunk]) -> str:
        if not retrieved:
            return "I do not have enough information in the provided support corpus to answer this safely."

        top = retrieved[0]
        topic_response = self._topic_response(ticket, top)
        if topic_response:
            return topic_response

        evidence = self._best_evidence(ticket, retrieved)
        if not evidence:
            evidence = self._clean_for_response(top.chunk.text, top.chunk.title)

        lead = self._lead_sentence(top)
        return self._compact(f"{lead} {evidence}", limit=760)

    def _topic_response(self, ticket: Ticket, top: RetrievedChunk) -> str:
        text = f"{ticket.subject} {ticket.issue}".lower()
        company = ticket.company.strip().lower()
        meta = f"{top.chunk.title} {top.chunk.path} {top.chunk.category}".lower()

        if company == "hackerrank" and any(
            term in text for term in ("compatib", "zoom", "connectivity", "webcam", "microphone", "audio", "video")
        ):
            return (
                "Run the HackerRank Compatibility check again and confirm the Zoom portion is the only failing item. "
                "Zoom-powered HackerRank interviews require current Chrome, Edge, or Firefox versions and network access to zoom.us domains. "
                "If the Zoom connectivity check still fails after browser and network changes, send HackerRank support or your recruiter a screenshot of the compatibility error so they can help with allowlist or scheduling options."
            )

        if company == "hackerrank" and "certificate" in text and "name" in text:
            return (
                "You can update the name on a HackerRank certificate once per account. "
                "Open the certificate page, enter the corrected full name, choose Regenerate Certificate, and confirm Update Name. "
                "The change applies to all certificates, so verify the spelling before confirming."
            )

        if company == "hackerrank" and "apply tab" in text:
            return (
                "Log in to HackerRank Community and open the Apply tab to view available developer jobs. "
                "From there, use filters such as role, experience level, location, and company, then select a job to review details and apply. "
                "If the Apply tab is missing or submissions are failing, capture the error state and contact HackerRank support with your account details."
            )

        if company == "hackerrank" and "subscription" in text and any(term in text for term in ("pause", "paused", "stopped hiring")):
            return (
                "HackerRank supports pausing eligible monthly self-serve subscriptions instead of canceling them. "
                "Go to Settings, open the Billing section under Subscription, choose Cancel Plan, then select the Pause Subscription option and a pause duration. "
                "Eligibility depends on having an active monthly subscription that started at least 30 days ago."
            )

        if company == "visa" and any(term in text for term in ("dispute", "charge", "wrong product")):
            return (
                "To dispute a Visa charge, contact your card issuer or bank using the number on your card or account statement. "
                "The issuer will usually ask for transaction details before it can investigate or resolve the dispute. "
                "Visa support guidance points cardholders to the issuer because Visa does not directly manage cardholder accounts or merchant refunds."
            )

        if company == "visa" and any(term in text for term in ("minimum", "merchant minimum", "surcharge", "us virgin islands")):
            return (
                "In general, Visa guidance says merchants should not set minimum or maximum Visa transaction amounts. "
                "There are exceptions in the USA and US territories, including the US Virgin Islands, where a merchant may require a minimum credit-card transaction of up to US$10. "
                "If the rule is being applied to a Visa debit card or above US$10 on a credit card, notify your card issuer."
            )

        if company == "visa" and any(term in text for term in ("urgent cash", "need cash", "emergency cash")):
            return (
                "Visa travel guidance points cardholders to ATMs with the Visa or PLUS mark for cash withdrawals where supported by the card issuer. "
                "If this is an emergency or your card is unavailable, Visa Global Customer Assistance Services can help with emergency cash services where applicable. "
                "Your bank or card issuer is still the best contact for limits, PIN issues, and account-specific approval."
            )

        if company == "claude" and any(term in text for term in ("lti", "canvas", "lms", "professor", "students")):
            return (
                "Claude LTI setup in Canvas is intended for Claude for Education administrators and LMS administrators. "
                "In Canvas, create a Claude LTI developer key, save it, turn it on, then install the app by Client ID under Admin > Settings > Apps. "
                "After that, enable Canvas in Claude for Education organization settings and enter the Canvas domain, Client ID, and Deployment ID."
            )

        if company == "claude" and "data" in text and any(term in text for term in ("improve", "model", "used")):
            return (
                "When you allow Claude chats or coding sessions to help improve Claude, the corpus says the data is de-linked from your user ID before review, access is limited, and it is used only to improve Claude. "
                "You can change model-improvement privacy settings at any time, and incognito chats are not used for model improvement. "
                "The retrieved support article does not state an exact retention duration for this consumer model-improvement use."
            )

        if company == "claude" and any(term in text for term in ("crawl", "crawler", "crawling", "robots.txt")):
            return (
                "To stop Anthropic crawlers from crawling your site, update the robots.txt file in the top-level directory for each domain or subdomain you want to opt out. "
                "The corpus says Anthropic Bots honor standard robots.txt directives, including a ClaudeBot rule with Disallow: /. "
                "If a bot appears to be malfunctioning, contact claudebot@anthropic.com from an email address associated with the affected domain."
            )

        if company == "claude" and "bedrock" in text and "customer-support-inquiries" in meta:
            return (
                "For Claude on Amazon Bedrock support, contact AWS Support first because Bedrock access and runtime issues are handled through AWS. "
                "If all production requests are failing, include timestamps, request IDs, regions, model IDs, and error messages so technical support can investigate quickly."
            )

        return ""

    def _best_evidence(self, ticket: Ticket, retrieved: List[RetrievedChunk]) -> str:
        query_terms = set(tokenize(f"{ticket.subject} {ticket.issue}"))
        important_terms = self._important_query_terms(ticket)
        scored = []
        top_path = retrieved[0].chunk.path if retrieved else ""
        for rank, hit in enumerate(retrieved):
            if hit.chunk.path != top_path:
                continue
            text = self._clean_for_response(hit.chunk.text, hit.chunk.title)
            sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
            for sentence in sentences:
                clean = self._sentence_text(sentence)
                if len(clean) < 35:
                    continue
                terms = set(tokenize(clean))
                overlap_terms = query_terms & terms
                overlap = len(overlap_terms) + sum(2 for term in overlap_terms if len(term) >= 7)
                overlap += sum(8 for term in overlap_terms if term in important_terms)
                if overlap:
                    scored.append((overlap, rank, clean))
        if not scored:
            return ""
        chosen = [
            sentence
            for _, _, sentence in sorted(scored, key=lambda item: (-item[0], item[1], item[2]))[:3]
        ]
        return self._compact(" ".join(self._dedupe_sentences(chosen)), limit=620)

    def _justification(self, safety: SafetyDecision, retrieved: List[RetrievedChunk]) -> str:
        if safety.request_type == "invalid":
            return "Out-of-scope or non-product request; replied with a safe scope clarification."

        if safety.status == "escalated":
            if retrieved and self._strong_escalation_source_for_reason(safety.reason, retrieved[0]):
                top = retrieved[0]
                return (
                    f"{safety.reason} Escalated despite related source "
                    f"\"{self._clean_title(top.chunk.title)}\" because the request needs human review."
                )
            return f"{safety.reason} Escalated without relying on weak or unrelated retrieval evidence."

        if retrieved:
            top = retrieved[0]
            return (
                f"Answered from the strongest matching corpus source: {top.chunk.company}/{top.chunk.category} "
                f"\"{self._clean_title(top.chunk.title)}\"."
            )
        return safety.reason

    def _lead_sentence(self, retrieved: RetrievedChunk) -> str:
        title = self._clean_title(retrieved.chunk.title)
        category = retrieved.chunk.category.replace("_", " ")
        return f"I found matching {retrieved.chunk.company} {category} guidance in \"{title}\"."

    def _escalation_team(self, ticket: Ticket, reason: str) -> str:
        text = f"{ticket.subject} {ticket.issue} {reason}".lower()
        company = ticket.company.strip() or "support"
        if company.lower() in {"none", "unknown"}:
            company = "human"
        if (
            "blocked-card" in text
            or "tarjeta" in text
            or "bloqueada" in text
            or ("prompt-injection" in text and company.lower() == "visa")
        ):
            return "cardholder travel support team"
        if any(term in text for term in ("infosec", "procurement", "vendor", "sales-review", "security review")):
            return "sales and security review team"
        if any(term in text for term in ("security", "vulnerability", "bug bounty", "exploit")):
            return "security response team"
        if any(term in text for term in ("fraud", "identity")):
            return "fraud and identity support team"
        if any(term in text for term in ("refund", "payment", "money", "subscription")):
            return "billing support team"
        if any(term in text for term in ("bedrock", "technical", "all requests", "failing", "connectivity")):
            return "technical support team"
        if any(term in text for term in ("inactivity", "lobby", "kicked out")):
            return "interview support team"
        if "reschedul" in text:
            return "assessment scheduling support team"
        if any(term in text for term in ("score", "recruiter", "assessment", "candidate")):
            return "assessment support team"
        if any(term in text for term in ("outage", "down", "all requests", "all submissions")):
            return "platform incident team"
        if re.search(r"\b(admin|access|account|remove|seat)\b", text):
            return "account administration team"
        return f"{company} support team"

    def _strong_escalation_source(self, ticket: Ticket, reason: str, retrieved: RetrievedChunk) -> bool:
        return self._strong_escalation_source_for_reason(
            f"{ticket.subject} {ticket.issue} {reason}",
            retrieved,
        )

    def _strong_escalation_source_for_reason(self, reason: str, retrieved: RetrievedChunk) -> bool:
        text = reason.lower()
        meta = f"{retrieved.chunk.title} {retrieved.chunk.path} {retrieved.chunk.category}".lower()
        weak_markers = (
            "glossary",
            "usage-policy",
            "credit-card-rules",
            "greenhouse",
            "interviewplanner",
            "automated-security-reviews",
            "changing-the-company-name",
            "centralized-test-settings",
        )
        if any(marker in meta for marker in weak_markers):
            return False
        if "outage" in text or "broad platform failure" in text:
            return False
        if "refund" in text or "payment" in text or "dispute" in text:
            return any(marker in meta for marker in ("refund", "billing", "dispute", "consumer-support", "visa/support.md"))
        if "admin" in text or "account-removal" in text or "access" in text:
            return any(marker in meta for marker in ("manage-members", "team-members", "user-access", "roles-and-permissions"))
        if "vulnerability" in text or "bug bounty" in text or "security" in text:
            return any(marker in meta for marker in ("public-vulnerability-reporting", "model-safety-bug-bounty", "security-and-compliance"))
        if "reschedul" in text:
            return "reschedul" in meta
        if "bedrock" in text or "technical" in text:
            return "bedrock" in meta and any(marker in meta for marker in ("support-inquiries", "contact", "documentation"))
        if "prompt-injection" in text or "blocked-card" in text:
            return "travel-support" in meta or "visa/support.md" in meta
        if "infosec" in text or "procurement" in text or "vendor" in text:
            return any(marker in meta for marker in ("security", "compliance", "contact-us"))
        return False

    def _clean_for_response(self, text: str, title: str) -> str:
        clean = "\n".join(line for line in text.splitlines() if "cdn-cgi" not in line.lower())
        clean = re.sub(r"^#+\s*", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"\b(title|description|url|last_modified)\s*:\s*\"?[^\n\"]+\"?", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"_?Last (modified|updated):[^_\.]+_?", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
        clean = re.sub(r"_([^_]+)_", r"\1", clean)
        clean = re.sub(r"\s+-\s+", " ", clean)
        clean = clean.replace("\\", "")
        title_clean = re.escape(self._clean_title(title))
        clean = re.sub(rf"^\s*{title_clean}\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean).strip(" :-")
        return clean

    def _clean_title(self, title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip()
        title = re.sub(r"\b(title|description)\s*:\s*", "", title, flags=re.IGNORECASE)
        for marker in (" Prerequisites", " Key benefits", " Adding ", " Editing ", " Deleting "):
            if marker in title:
                title = title.split(marker, 1)[0]
                break
        return title.strip(" \"")

    def _dedupe_sentences(self, sentences: List[str]) -> List[str]:
        seen = set()
        deduped = []
        for sentence in sentences:
            key = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(sentence)
        return deduped

    def _important_query_terms(self, ticket: Ticket) -> set[str]:
        ignore = {
            "Card",
            "Cheques",
            "Claude",
            "HackerRank",
            "Hackerrank",
            "Traveller",
            "Traveller's",
            "Travellers",
            "Traveler",
            "Travelers",
            "Visa",
        }
        terms = set()
        for match in re.finditer(r"\b[A-Z][A-Za-z0-9']{3,}\b", f"{ticket.subject} {ticket.issue}"):
            term = match.group(0).strip("'")
            if term not in ignore:
                terms.add(term.lower())
        return terms

    def _sentence_text(self, sentence: str) -> str:
        clean = re.sub(r"\s+", " ", sentence).strip(" -")
        if len(clean) <= 260:
            return clean
        for index in (clean.rfind(".", 0, 260), clean.rfind(";", 0, 260)):
            if index >= 90:
                return clean[: index + 1]
        return ""

    def _compact(self, text: str, limit: int) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."
