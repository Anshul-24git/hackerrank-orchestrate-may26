"""Shared data structures and constants for the support triage baseline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


OUTPUT_COLUMNS = [
    "issue",
    "subject",
    "company",
    "response",
    "product_area",
    "status",
    "request_type",
    "justification",
]

ALLOWED_STATUSES = {"replied", "escalated"}
ALLOWED_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}


@dataclass(frozen=True)
class Ticket:
    """Input ticket normalized from a CSV row."""

    issue: str
    subject: str
    company: str
    raw: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    """A retrievable chunk from the support corpus."""

    company: str
    path: str
    category: str
    title: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    """A document chunk plus retrieval evidence."""

    chunk: DocumentChunk
    score: float
    matched_terms: List[str]


@dataclass(frozen=True)
class SafetyDecision:
    """Safety and routing decision before response generation."""

    status: str
    request_type: str
    reason: str


@dataclass(frozen=True)
class Prediction:
    """Final output row produced by the agent."""

    issue: str
    subject: str
    company: str
    response: str
    product_area: str
    status: str
    request_type: str
    justification: str

    def as_row(self) -> Dict[str, str]:
        return {
            "issue": self.issue,
            "subject": self.subject,
            "company": self.company,
            "response": self.response,
            "product_area": self.product_area,
            "status": self.status,
            "request_type": self.request_type,
            "justification": self.justification,
        }
