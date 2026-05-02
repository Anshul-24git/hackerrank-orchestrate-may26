"""End-to-end support triage agent baseline."""

from __future__ import annotations

from pathlib import Path
from typing import List

from corpus_loader import CorpusLoader
from retriever import LexicalRetriever
from router import TicketRouter
from schemas import Prediction, Ticket
from writer import read_tickets, write_predictions


class SupportTriageAgent:
    """Loads corpus once, then routes tickets deterministically."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        chunks = CorpusLoader(self.data_dir).load()
        self.retriever = LexicalRetriever(chunks)
        self.router = TicketRouter(self.retriever)
        self.chunk_count = len(chunks)

    def predict(self, ticket: Ticket) -> Prediction:
        return self.router.route(ticket)

    def run_csv(self, input_path: Path, output_path: Path) -> List[Prediction]:
        tickets = read_tickets(input_path)
        predictions = [self.predict(ticket) for ticket in tickets]
        write_predictions(output_path, predictions)
        return predictions
