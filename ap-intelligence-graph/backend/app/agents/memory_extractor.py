from app.llm.factory import call_with_fallback


def extract_candidate_claims(
    message: str,
    client_id: str,
    client_name: str,
    known_predicates: list[str] | None = None,
    known_partners: list[dict[str, str]] | None = None,
) -> tuple[list[dict], str]:
    claims, provider_name = call_with_fallback(
        "extract_claims", message, client_id, client_name, known_predicates, known_partners
    )
    return claims, provider_name
