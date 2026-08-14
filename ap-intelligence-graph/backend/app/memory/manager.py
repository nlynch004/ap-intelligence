"""Orchestrates the memory write pipeline (spec Sec.10):

conversation -> extraction agent -> candidate claims -> schema validation
-> conflict lookup -> operation decision -> (human approval where required)
-> canonical store -> graph refresh

This module owns that orchestration; app/memory/operations.py owns the
actual state transitions.
"""

from sqlalchemy.orm import Session

from app.agents.memory_extractor import extract_candidate_claims
from app.memory.conflict_resolver import decide_operation, find_active_conflict
from app.memory.operations import execute_create, execute_reject, execute_supersede, execute_update
from app.models import Client, MemoryCandidate, MemoryClaim, RawEvent


def propose_candidates_from_message(db: Session, *, client_id: str, message: str) -> tuple[list[MemoryCandidate], str]:
    """Runs the extraction agent, deterministically checks each candidate
    against existing active memory, and persists them as pending
    MemoryCandidate rows (spec Sec.18 - never silently persisted)."""
    client = db.get(Client, client_id)
    client_name = client.name if client else client_id

    db.add(RawEvent(client_id=client_id, event_type="chat_message", payload={"message": message}))

    known_predicates = sorted({
        c.predicate for c in
        db.query(MemoryClaim).filter(MemoryClaim.client_id == client_id, MemoryClaim.status == "active").all()
    })
    raw_claims, provider_name = extract_candidate_claims(message, client_id, client_name, known_predicates)

    candidates: list[MemoryCandidate] = []
    for raw in raw_claims:
        payload = dict(raw)
        if payload.get("subject_type") == "client":
            payload["subject_id"] = client_id
        payload.setdefault("subject_label", client_name)

        existing = find_active_conflict(
            db,
            subject_type=payload["subject_type"],
            subject_id=payload["subject_id"],
            predicate=payload["predicate"],
            client_id=client_id if payload["subject_type"] == "client" else None,
        )
        operation = decide_operation(payload, existing)

        candidate = MemoryCandidate(
            client_id=client_id,
            claim_payload=payload,
            proposed_operation=operation,
            conflict_with_claim_id=existing.id if operation == "SUPERSEDE" else None,
            status="pending",
            source_message=message,
        )
        db.add(candidate)
        candidates.append(candidate)

    db.flush()
    return candidates, provider_name


def _source_for_candidate(candidate: MemoryCandidate) -> dict:
    return {
        "type": "account_team_statement",
        "source_id": f"chat:{candidate.id}",
        "speaker": "account_manager",
        "message_excerpt": (candidate.source_message or "")[:280],
    }


def approve_candidate(db: Session, candidate: MemoryCandidate) -> dict:
    """Returns a dict with keys: operation_executed, claim, superseded_claim,
    requires_conflict_resolution, conflict_with_claim."""
    source = _source_for_candidate(candidate)

    if candidate.proposed_operation == "SUPERSEDE":
        # Do not auto-execute a supersede on review approval - surface the
        # conflict dialog first (spec Sec.19 Scene 3 is a distinct step).
        candidate.status = "approved"
        db.flush()
        conflicting = db.get(MemoryClaim, candidate.conflict_with_claim_id) if candidate.conflict_with_claim_id else None
        return {
            "operation_executed": None,
            "claim": None,
            "superseded_claim": None,
            "requires_conflict_resolution": True,
            "conflict_with_claim": conflicting,
        }

    if candidate.proposed_operation == "UPDATE":
        existing = find_active_conflict(
            db,
            subject_type=candidate.claim_payload["subject_type"],
            subject_id=candidate.claim_payload["subject_id"],
            predicate=candidate.claim_payload["predicate"],
            client_id=candidate.client_id,
        )
        claim = execute_update(db, existing, candidate.claim_payload, source=source)
        candidate.status = "approved"
        db.flush()
        return {"operation_executed": "UPDATE", "claim": claim, "superseded_claim": None, "requires_conflict_resolution": False, "conflict_with_claim": None}

    # CREATE
    claim = execute_create(db, candidate.claim_payload, client_id=candidate.client_id, source=source)
    candidate.status = "approved"
    db.flush()
    return {"operation_executed": "CREATE", "claim": claim, "superseded_claim": None, "requires_conflict_resolution": False, "conflict_with_claim": None}


def reject_candidate(db: Session, candidate: MemoryCandidate) -> None:
    candidate.status = "rejected"
    execute_reject(db, candidate.client_id, f"Candidate rejected: {candidate.claim_payload.get('predicate')} = {candidate.claim_payload.get('value')}")
    db.flush()


def resolve_conflict(db: Session, candidate: MemoryCandidate, operation: str) -> dict:
    source = _source_for_candidate(candidate)

    if operation == "REJECT":
        candidate.status = "rejected"
        execute_reject(db, candidate.client_id, "Conflicting candidate rejected; prior belief retained.")
        return {"new_claim": None, "superseded_claim": None}

    if operation != "SUPERSEDE":
        raise ValueError(f"Unsupported conflict resolution operation: {operation}")

    existing = db.get(MemoryClaim, candidate.conflict_with_claim_id)
    if existing is None:
        raise ValueError("Conflicting claim not found")

    new_claim, old_claim = execute_supersede(db, existing, candidate.claim_payload, client_id=candidate.client_id, source=source)
    candidate.status = "approved"
    db.flush()
    return {"new_claim": new_claim, "superseded_claim": old_claim}
