"""Unit tests for the conflict resolver + operation state transitions -
the correctness-critical path behind demo Scene 3 (spec Sec.11, Sec.19)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.memory.conflict_resolver import decide_operation, find_active_conflict
from app.memory.operations import execute_create, execute_supersede, execute_update
from app.models import Client, MemoryClaim


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(Client(id="acme", name="Acme Co", synthetic=False))
    session.flush()
    yield session
    session.close()


def _payload(**overrides):
    base = dict(
        type="client_preference", subject_type="client", subject_id="acme",
        subject_label="Acme Co", predicate="partnership_strategy", value="grow_coupons",
        claim_class="verified_fact", confidence=0.9,
    )
    base.update(overrides)
    return base


SOURCE = {"type": "account_team_statement", "source_id": "test", "speaker": "tester"}


def test_no_existing_claim_yields_create(db):
    existing = find_active_conflict(db, subject_type="client", subject_id="acme", predicate="partnership_strategy", client_id="acme")
    assert existing is None
    assert decide_operation(_payload(), existing) == "CREATE"


def test_same_value_repeated_yields_update(db):
    execute_create(db, _payload(value="grow_coupons"), client_id="acme", source=SOURCE)
    existing = find_active_conflict(db, subject_type="client", subject_id="acme", predicate="partnership_strategy", client_id="acme")
    assert existing is not None
    assert decide_operation(_payload(value="grow_coupons"), existing) == "UPDATE"


def test_differing_value_yields_supersede_proposal(db):
    execute_create(db, _payload(value="grow_coupons"), client_id="acme", source=SOURCE)
    existing = find_active_conflict(db, subject_type="client", subject_id="acme", predicate="partnership_strategy", client_id="acme")
    assert decide_operation(_payload(value="reduce_coupons"), existing) == "SUPERSEDE"


def test_execute_create_sets_active_status(db):
    claim = execute_create(db, _payload(), client_id="acme", source=SOURCE)
    assert claim.status == "active"
    assert claim.supersedes == []
    assert claim.client_id == "acme"


def test_execute_update_refines_without_new_row(db):
    claim = execute_create(db, _payload(confidence=0.7), client_id="acme", source=SOURCE)
    updated = execute_update(db, claim, _payload(confidence=0.95), source=SOURCE)
    assert updated.id == claim.id
    assert updated.confidence == 0.95
    assert db.query(MemoryClaim).count() == 1


def test_execute_supersede_transitions_old_and_creates_new(db):
    old = execute_create(db, _payload(value="grow_coupons"), client_id="acme", source=SOURCE)
    new, old_ref = execute_supersede(db, old, _payload(value="reduce_coupons"), client_id="acme", source=SOURCE)

    assert old_ref.id == old.id
    assert old_ref.status == "superseded"
    assert old_ref.valid_to is not None
    assert old_ref.superseded_by == new.id

    assert new.status == "active"
    assert new.supersedes == [old.id]
    assert new.value == "reduce_coupons"

    # normal (active-only) retrieval must exclude the old claim
    active = db.query(MemoryClaim).filter(MemoryClaim.status == "active").all()
    assert [c.id for c in active] == [new.id]

    # but it must remain queryable for history
    all_claims = db.query(MemoryClaim).all()
    assert old.id in {c.id for c in all_claims}
