"""Executes the explicit memory operations (spec Sec.9).

Only application code writes to memory_claims - never the LLM directly
(spec Sec.10: "New memory must not be written directly by the conversational
agent."). Each function here does one state transition, logs an
ActivityEvent, and (where relevant) writes the matching graph edge.
"""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import ActivityEvent, MemoryClaim, MemoryEdge, PortfolioPattern

# Source authority hierarchy (spec Sec.12). A high-confidence model inference
# must never automatically outrank verified system data.
SOURCE_AUTHORITY = {
    "structured_system_of_record": 0.95,
    "account_team_statement": 0.85,
    "account_team_annotation": 0.75,
    "portfolio_evidence": 0.65,
    "single_historical_observation": 0.5,
    "agent_inference": 0.35,
}

# predicate -> graph relationship label, for claims that represent a named
# relationship type from spec Sec.16. Falls back to a generic label.
PREDICATE_RELATIONSHIP = {
    "primary_growth_objective": "HAS_GOAL",
    "partnership_strategy": "HAS_STRATEGY",
    "attribution_integrity_risk": "HAS_RISK",
    "relationship_status": "HAS_RELATIONSHIP",
}


def authority_for_source(source_type: str) -> float:
    return SOURCE_AUTHORITY.get(source_type, 0.5)


def _today() -> str:
    return date.today().isoformat()


def log_activity(db: Session, client_id: str | None, event_type: str, summary: str, detail: dict | None = None) -> ActivityEvent:
    event = ActivityEvent(client_id=client_id, event_type=event_type, summary=summary, detail=detail or {})
    db.add(event)
    db.flush()
    return event


def _new_claim_from_payload(payload: dict, *, client_id: str | None, source: dict, supersedes: list[str]) -> MemoryClaim:
    scope = {"client_id": client_id} if client_id else {"portfolio": "privacy_safe"}
    return MemoryClaim(
        type=payload["type"],
        subject_type=payload["subject_type"],
        subject_id=payload["subject_id"],
        predicate=payload["predicate"],
        value=payload["value"],
        scope=scope,
        client_id=client_id,
        claim_class=payload["claim_class"],
        confidence=payload["confidence"],
        authority_score=authority_for_source(source.get("type", "agent_inference")),
        source=source,
        valid_from=_today(),
        status="active",
        supersedes=supersedes,
        synthetic=False,
    )


def execute_create(db: Session, payload: dict, *, client_id: str | None, source: dict) -> MemoryClaim:
    claim = _new_claim_from_payload(payload, client_id=client_id, source=source, supersedes=[])
    db.add(claim)
    db.flush()

    relationship = PREDICATE_RELATIONSHIP.get(claim.predicate, "HAS_MEMORY")
    if client_id:
        db.add(MemoryEdge(
            from_type="client", from_id=client_id, to_type="memory_claim", to_id=claim.id,
            relationship=relationship, client_id=client_id,
        ))

    log_activity(
        db, client_id, "CREATE",
        f"{payload['subject_label']} {claim.predicate.replace('_', ' ')}: {claim.value.replace('_', ' ')}",
        detail={"claim_id": claim.id, "claim_class": claim.claim_class, "confidence": claim.confidence},
    )
    return claim


def execute_update(db: Session, existing: MemoryClaim, payload: dict, *, source: dict) -> MemoryClaim:
    existing.confidence = max(existing.confidence, payload["confidence"])
    existing.source = source
    existing.valid_from = _today()
    db.flush()
    log_activity(
        db, existing.client_id, "UPDATE",
        f"Refined belief: {existing.predicate.replace('_', ' ')} = {existing.value.replace('_', ' ')}",
        detail={"claim_id": existing.id},
    )
    return existing


def execute_supersede(db: Session, existing: MemoryClaim, payload: dict, *, client_id: str | None, source: dict) -> tuple[MemoryClaim, MemoryClaim]:
    new_claim = _new_claim_from_payload(payload, client_id=client_id, source=source, supersedes=[existing.id])
    db.add(new_claim)
    db.flush()

    existing.status = "superseded"
    existing.valid_to = _today()
    existing.superseded_by = new_claim.id

    relationship = PREDICATE_RELATIONSHIP.get(new_claim.predicate, "HAS_MEMORY")
    if client_id:
        db.add(MemoryEdge(
            from_type="client", from_id=client_id, to_type="memory_claim", to_id=new_claim.id,
            relationship=relationship, client_id=client_id,
        ))
    db.add(MemoryEdge(
        from_type="memory_claim", from_id=new_claim.id, to_type="memory_claim", to_id=existing.id,
        relationship="SUPERSEDES", client_id=client_id,
    ))
    db.flush()

    log_activity(
        db, client_id, "SUPERSEDE",
        f"{existing.value.replace('_', ' ')} → {new_claim.value.replace('_', ' ')}",
        detail={"old_claim_id": existing.id, "new_claim_id": new_claim.id},
    )
    return new_claim, existing


def execute_reject(db: Session, client_id: str | None, reason: str) -> None:
    log_activity(db, client_id, "REJECT", reason)


def execute_promote_pattern_evidence(db: Session, pattern: PortfolioPattern, *, positive: bool, new_decision_id: str) -> tuple[int, int]:
    """Increment a portfolio pattern's evidence count with one new real
    outcome (spec Sec.14, Scene 6). Returns (count_before, count_after)."""
    before = pattern.evidence_count
    pattern.evidence_count += 1
    if positive and pattern.positive_outcomes is not None:
        pattern.positive_outcomes += 1
    pattern.supporting_decision_ids = [*pattern.supporting_decision_ids, new_decision_id]
    db.flush()
    log_activity(
        db, None, "PROMOTE",
        f"Portfolio pattern '{pattern.name.replace('_', ' ')}' evidence count: {before} → {pattern.evidence_count}",
        detail={"pattern_id": pattern.id, "before": before, "after": pattern.evidence_count},
    )
    return before, pattern.evidence_count
