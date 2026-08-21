import re
from datetime import date, datetime

from app.models import MemoryClaim

_WORD_RE = re.compile(r"[a-z0-9]+")

WEIGHTS = {
    "semantic_similarity": 0.30,
    "entity_match": 0.25,
    "client_scope_match": 0.15,
    "authority_score": 0.20,
    "recency_score": 0.10,
}


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def query_terms(*texts: str) -> set[str]:
    terms: set[str] = set()
    for t in texts:
        if t:
            terms |= _tokenize(t)
    return terms


def _semantic_similarity(claim: MemoryClaim, terms: set[str]) -> float:
    claim_terms = _tokenize(f"{claim.predicate} {claim.value} {claim.subject_id}")
    if not claim_terms or not terms:
        return 0.0
    overlap = len(claim_terms & terms)
    return min(overlap / max(len(claim_terms), 1), 1.0)


def _entity_match(claim: MemoryClaim, entity_ids: set[str]) -> float:
    return 1.0 if claim.subject_id in entity_ids else 0.0


def _client_scope_match(claim: MemoryClaim, client_id: str | None) -> float:
    if claim.client_id == client_id:
        return 1.0
    if claim.client_id is None:
        return 0.6
    return 0.0


def _recency_score(claim: MemoryClaim) -> float:
    try:
        valid_from = datetime.strptime(claim.valid_from, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0.5
    days_old = max((date.today() - valid_from).days, 0)
    return max(1.0 - (days_old / 730), 0.2)


def score_claim(claim: MemoryClaim, *, terms: set[str], entity_ids: set[str], client_id: str | None) -> float:
    stale_penalty = 0.0 if claim.status == "active" else 0.5
    conflict_penalty = 0.3 if claim.superseded_by else 0.0
    return (
        WEIGHTS["semantic_similarity"] * _semantic_similarity(claim, terms)
        + WEIGHTS["entity_match"] * _entity_match(claim, entity_ids)
        + WEIGHTS["client_scope_match"] * _client_scope_match(claim, client_id)
        + WEIGHTS["authority_score"] * claim.authority_score
        + WEIGHTS["recency_score"] * _recency_score(claim)
        - stale_penalty
        - conflict_penalty
    )
