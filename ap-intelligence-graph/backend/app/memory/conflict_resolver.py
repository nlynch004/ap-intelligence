from sqlalchemy.orm import Session

from app.models import MemoryClaim


def find_active_conflict(db: Session, *, subject_type: str, subject_id: str, predicate: str, client_id: str | None) -> MemoryClaim | None:
    q = db.query(MemoryClaim).filter(
        MemoryClaim.subject_type == subject_type,
        MemoryClaim.subject_id == subject_id,
        MemoryClaim.predicate == predicate,
        MemoryClaim.status == "active",
    )
    if client_id is not None:
        q = q.filter(MemoryClaim.client_id == client_id)
    return q.first()


def decide_operation(candidate: dict, existing: MemoryClaim | None) -> str:
    if existing is None:
        return "CREATE"
    if str(existing.value).strip().lower() == str(candidate["value"]).strip().lower():
        return "UPDATE"
    return "SUPERSEDE"
