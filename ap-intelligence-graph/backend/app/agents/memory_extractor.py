"""Memory extraction agent (spec Sec.21). Input: a message + entity context.
Output: candidate structured claims. Never writes to the database."""

from app.llm.factory import call_with_fallback


def extract_candidate_claims(
    message: str, client_id: str, client_name: str, known_predicates: list[str] | None = None
) -> tuple[list[dict], str]:
    claims, provider_name = call_with_fallback("extract_claims", message, client_id, client_name, known_predicates)
    return claims, provider_name
