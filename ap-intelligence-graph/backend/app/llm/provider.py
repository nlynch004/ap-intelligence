"""Provider-agnostic LLM interface (spec Sec.23, Sec.21).

Three methods only - the minimum the product needs an LLM for. Everything
else (validation, IDs, state transitions, conflict lookup, retrieval
filtering) is deterministic application code in app/memory/, per spec Sec.22:
"The model proposes; application logic validates and persists."
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def extract_claims(
        self, message: str, client_id: str, client_name: str, known_predicates: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Return candidate claim dicts shaped like CandidateClaimPayload.
        Should return an empty list for messages that contain no durable,
        structured, client-relevant fact (do not force claims out of chatter).

        `known_predicates` lists the predicate names already active for this
        client's claims - implementations should be steered to reuse an exact
        match when applicable, since conflict detection downstream is a
        deterministic exact-string match, not semantic (spec Sec.11).
        """

    @abstractmethod
    def recommend(self, question: str, evidence_brief: str, context: dict[str, Any]) -> dict[str, Any]:
        """Return a dict shaped like the recommendation output in spec Sec.20
        (minus supporting_memory_ids, which the deterministic retrieval layer
        attaches itself rather than trusting the model to invent IDs)."""

    @abstractmethod
    def summarize(self, client_name: str, active_claims: list[dict[str, Any]]) -> str:
        """Concise prose summary of currently active memory, for the
        'bring me up to speed' scene."""
