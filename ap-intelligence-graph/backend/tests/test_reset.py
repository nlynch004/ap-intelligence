"""Tests for Step 3: deterministic demo reset.

Runs against a throwaway temp-file SQLite DB (never the real
backend/data/app.db the live demo servers use) by monkeypatching the engine
`app.seed` operates on - `seed(db, reset=True)` itself is exactly the
function the new `/api/demo/reset` endpoint calls.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config_module
import app.seed as seed_module
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.memory import manager
from app.memory.manager import approve_candidate, resolve_conflict
from app.memory.operations import execute_promote_pattern_evidence
from app.models import ActivityEvent, Decision, MemoryCandidate, MemoryClaim, Outcome, PortfolioPattern


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_reset.db"
    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(seed_module, "engine", engine)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)  # force deterministic mock

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    seed_module.seed(session, reset=True)
    yield session
    session.close()


def _dirty_the_state(db):
    """Runs the exact strategy-conflict/SUPERSEDE sequence plus a decision
    and a simulated outcome, so reset has real state to undo."""
    candidates, _ = manager.propose_candidates_from_message(
        db, client_id="northwind",
        message=(
            "Northwind's strategy changed after last week's executive review. They now want to "
            "reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS "
            "is a little lower."
        ),
    )
    strategy_candidate = next(c for c in candidates if c.claim_payload["predicate"] == "partnership_strategy")
    for c in candidates:
        if c.id != strategy_candidate.id:
            approve_candidate(db, c)
    approve_candidate(db, strategy_candidate)  # surfaces the conflict, doesn't execute it
    resolve_conflict(db, strategy_candidate, "SUPERSEDE")

    decision = Decision(
        client_id="northwind", partner_id="summit_sisters", decision_type="creator_renewal",
        summary="Renew Summit Sisters under hybrid compensation",
        terms={"base_fee": 3500, "performance_bonus_pct": 10, "bonus_basis": "verified_new_customer_revenue"},
        rationale="test", motivated_by_claim_ids=["pattern_hybrid_comp"], status="approved", synthetic=False,
    )
    db.add(decision)
    db.flush()

    outcome = Outcome(
        decision_id=decision.id,
        metrics={"verified_new_customer_revenue": 21000, "attributed_revenue": 29000},
        outcome_label="positive", is_simulated=True,
    )
    db.add(outcome)

    pattern = db.get(PortfolioPattern, "pattern_hybrid_comp")
    execute_promote_pattern_evidence(db, pattern, positive=True, new_decision_id=decision.id)

    db.commit()


def test_reset_restores_exact_seeded_state(db):
    _dirty_the_state(db)

    # sanity: state really is dirty before reset
    assert db.query(MemoryCandidate).count() > 0
    assert db.query(Decision).filter_by(client_id="northwind").count() == 1
    assert db.query(Outcome).count() == 1
    dirty_pattern = db.get(PortfolioPattern, "pattern_hybrid_comp")
    assert dirty_pattern.evidence_count == 32
    assert dirty_pattern.positive_outcomes == 22

    seed_module.seed(db, reset=True)

    # old coupon-growth strategy is active again
    strategy = db.get(MemoryClaim, "mem_northwind_strategy_coupon")
    assert strategy.status == "active"
    assert strategy.value == "aggressively_grow_coupon_partnerships"
    assert strategy.valid_to is None
    assert strategy.superseded_by is None

    # exactly one partnership_strategy claim for northwind - no leftover new one
    strategy_claims = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.subject_id == "northwind", MemoryClaim.predicate == "partnership_strategy")
        .all()
    )
    assert len(strategy_claims) == 1

    # no pending (or any) memory candidates
    assert db.query(MemoryCandidate).count() == 0

    # no demo-created decision or outcome
    assert db.query(Decision).filter_by(client_id="northwind").count() == 0
    assert db.query(Outcome).count() == 0

    # portfolio pattern restored to its exact seed values
    pattern = db.get(PortfolioPattern, "pattern_hybrid_comp")
    assert pattern.evidence_count == 31
    assert pattern.positive_outcomes == 21

    # activity feed restored to exactly the 2 seed events
    activity = db.query(ActivityEvent).all()
    assert len(activity) == 2
    assert {a.event_type for a in activity} == {"SEED"}

    # graph topology restored: same node/edge counts as a fresh seed
    from app.models import Campaign, Client, MemoryEdge, Partner

    assert db.query(Client).count() == 6
    assert db.query(Partner).count() == 15
    assert db.query(Campaign).count() == 4
    assert db.query(MemoryClaim).count() == 18
    assert db.query(MemoryEdge).filter(MemoryEdge.client_id == "northwind").count() == 15


def test_reset_is_idempotent(db):
    """Resetting twice in a row (no dirtying in between) must be a no-op,
    not an error and not a state change."""
    seed_module.seed(db, reset=True)
    seed_module.seed(db, reset=True)
    assert db.query(MemoryClaim).count() == 18
    assert db.get(PortfolioPattern, "pattern_hybrid_comp").evidence_count == 31
