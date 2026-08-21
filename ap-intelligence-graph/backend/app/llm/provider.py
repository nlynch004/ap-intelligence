from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def extract_claims(
        self,
        message: str,
        client_id: str,
        client_name: str,
        known_predicates: list[str] | None = None,
        known_partners: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def recommend(self, question: str, evidence_brief: str, context: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def summarize(self, client_name: str, active_claims: list[dict[str, Any]]) -> str:
        ...

    @abstractmethod
    def review_campaign(self, evidence: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def generate_partner_brief(self, evidence: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def summarize_history(self, evidence: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def compare_scenarios(self, evidence: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def propose_plan(self, context: dict[str, Any]) -> dict[str, Any]:
        ...
