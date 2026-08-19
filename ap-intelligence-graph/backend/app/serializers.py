"""ORM -> Pydantic conversions. Centralized so datetime formatting and
candidate-payload shaping stay consistent across routers."""

from app import models, schemas


def claim_to_out(c: models.MemoryClaim) -> schemas.MemoryClaimOut:
    return schemas.MemoryClaimOut(
        id=c.id, type=c.type, subject_type=c.subject_type, subject_id=c.subject_id,
        predicate=c.predicate, value=c.value, scope=c.scope, claim_class=c.claim_class,
        confidence=c.confidence, authority_score=c.authority_score, source=c.source,
        valid_from=c.valid_from, valid_to=c.valid_to, status=c.status, supersedes=c.supersedes,
        superseded_by=c.superseded_by, synthetic=c.synthetic, created_at=c.created_at.isoformat(),
    )


def candidate_to_out(cand: models.MemoryCandidate, conflict: models.MemoryClaim | None = None) -> schemas.MemoryCandidateOut:
    return schemas.MemoryCandidateOut(
        id=cand.id, client_id=cand.client_id,
        claim_payload=schemas.CandidateClaimPayload(**cand.claim_payload),
        proposed_operation=cand.proposed_operation,
        conflict_with_claim_id=cand.conflict_with_claim_id,
        conflict_with_claim=claim_to_out(conflict) if conflict else None,
        status=cand.status, created_at=cand.created_at.isoformat(),
    )


def decision_to_out(d: models.Decision) -> schemas.DecisionOut:
    return schemas.DecisionOut(
        id=d.id, client_id=d.client_id, partner_id=d.partner_id, decision_type=d.decision_type,
        summary=d.summary, terms=d.terms, rationale=d.rationale,
        motivated_by_claim_ids=d.motivated_by_claim_ids, status=d.status, synthetic=d.synthetic,
        source_planned_action_id=d.source_planned_action_id, created_at=d.created_at.isoformat(),
    )


def outcome_to_out(o: models.Outcome) -> schemas.OutcomeOut:
    return schemas.OutcomeOut(
        id=o.id, decision_id=o.decision_id, metrics=o.metrics, outcome_label=o.outcome_label,
        is_simulated=o.is_simulated, created_at=o.created_at.isoformat(),
    )


def activity_to_out(a: models.ActivityEvent) -> schemas.ActivityEventOut:
    return schemas.ActivityEventOut(
        id=a.id, event_type=a.event_type, summary=a.summary, detail=a.detail,
        created_at=a.created_at.isoformat(),
    )
