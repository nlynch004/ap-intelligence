"""Deterministic fallback provider - used whenever OPENAI_API_KEY is absent.

This is not a stub that no-ops: it implements real (if simple) rule-based
NLU tuned to the rehearsed demo script in spec Sec.19, so the full loop
(Scenes 1-6) is genuinely demoable with zero API calls. Swapping in a real
OpenAI key later changes nothing about the app's behavior contract - only
the generality/quality of extraction and prose (see llm/factory.py).
"""

from typing import Any

from app.formatting import extract_dollar_amount
from app.llm.provider import LLMProvider


class MockProvider(LLMProvider):
    name = "mock_deterministic"

    def extract_claims(
        self, message: str, client_id: str, client_name: str, known_predicates: list[str] | None = None
    ) -> list[dict[str, Any]]:
        text = message.lower()
        candidates: list[dict[str, Any]] = []

        wants_less_coupon = "coupon" in text and any(
            kw in text for kw in ["reduce", "less", "de-emphasize", "dependence", "pull back", "pull-back"]
        )
        if wants_less_coupon:
            candidates.append({
                "type": "client_preference",
                "subject_type": "client",
                "subject_id": client_id,
                "subject_label": client_name,
                "predicate": "partnership_strategy",
                "value": "reduce_coupon_dependence",
                "claim_class": "verified_fact",
                "confidence": 0.93,
                "rationale": "Account team stated the client's strategy shifted away from coupon growth.",
            })

        wants_new_customers = any(kw in text for kw in ["new-customer", "new customer", "new customers"])
        if wants_new_customers:
            candidates.append({
                "type": "client_preference",
                "subject_type": "client",
                "subject_id": client_id,
                "subject_label": client_name,
                "predicate": "primary_growth_objective",
                "value": "new_customer_acquisition",
                "claim_class": "verified_fact",
                "confidence": 0.94,
                "rationale": "Account team stated new-customer acquisition is now the priority.",
            })

        accepts_lower_roas = "roas" in text and any(kw in text for kw in ["lower", "short-term", "short term", "dip"])
        if accepts_lower_roas:
            candidates.append({
                "type": "client_preference",
                "subject_type": "client",
                "subject_id": client_id,
                "subject_label": client_name,
                "predicate": "accepts_tradeoff",
                "value": "lower_short_term_roas",
                "claim_class": "account_preference",
                "confidence": 0.85,
                "rationale": "Account team indicated the client will accept lower short-term ROAS for this tradeoff.",
            })

        return candidates

    def recommend(self, question: str, evidence_brief: str, context: dict[str, Any]) -> dict[str, Any]:
        ask = extract_dollar_amount(question) or context.get("campaign_ask") or 6000.0
        base_fee = round((ask * 0.5833) / 100) * 100
        bonus_pct = 10

        has_hypothesis = context.get("has_attribution_hypothesis", False)
        has_pattern = context.get("has_hybrid_pattern", False)

        uncertainties = []
        if has_hypothesis:
            uncertainties.append("Promo-code leakage is suspected but not verified.")

        explanation_parts = []
        if context.get("primary_goal"):
            explanation_parts.append(f"{context['client_name']}'s current objective is {context['primary_goal']}.")
        if context.get("strategy"):
            explanation_parts.append(f"Their strategy is to {context['strategy']}.")
        explanation_parts.append(f"{context.get('partner_name', 'The partner')} has promising prior commerce performance, but the strongest result has unresolved attribution quality.")
        if has_pattern:
            explanation_parts.append("Comparable synthetic AP portfolio decisions performed better under hybrid compensation than flat-fee renewal.")
        explanation = " ".join(explanation_parts)

        return {
            "recommendation": "renegotiate_and_test",
            "recommended_terms": {
                "base_fee": base_fee,
                "performance_bonus_pct": bonus_pct,
                "bonus_basis": "verified_new_customer_revenue",
            },
            "confidence": 0.74,
            "uncertainties": uncertainties,
            "explanation": explanation,
        }

    def summarize(self, client_name: str, active_claims: list[dict[str, Any]]) -> str:
        if not active_claims:
            return f"No active memory found yet for {client_name}."
        lines = [f"Here's what AP currently knows about {client_name}:"]
        for c in active_claims:
            lines.append(f"- {c['predicate'].replace('_', ' ')}: {c['value'].replace('_', ' ')}")
        return "\n".join(lines)
