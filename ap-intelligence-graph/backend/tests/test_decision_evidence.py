"""Tests for Step 5: structured DecisionEvidence.

`build_recommendation_context` never calls the LLM - these tests exercise
pure deterministic retrieval/construction logic against the real seed data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.seed as seed_module
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.memory.manager import approve_candidate, propose_candidates_from_message, resolve_conflict
from app.memory.operations import execute_promote_pattern_evidence
from app.memory.retrieval import build_recommendation_context
from app.models import Decision, Outcome, PortfolioPattern

QUESTION = "Summit Sisters wants $6,000 for another campaign. Should we renew them?"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_decision_evidence.db"
    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(seed_module, "engine", engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    seed_module.seed(session, reset=True)
    yield session
    session.close()


def _evidence(db):
    ctx = build_recommendation_context(db, client_id="northwind", partner_id="summit_sisters", question=QUESTION)
    return ctx["decision_evidence"]


# ---- 1. decision evidence accuracy ----

def test_commercial_ask(db):
    ev = _evidence(db)
    assert ev.commercial_ask.proposed_fee == 6000.0
    assert ev.commercial_ask.prior_fee == 4200.0
    assert ev.commercial_ask.increase_pct == pytest.approx(42.857, abs=0.01)


def test_all_three_summit_sisters_campaigns_present(db):
    ev = _evidence(db)
    assert len(ev.prior_performance) == 3
    months = {c.month for c in ev.prior_performance}
    assert months == {"2025-09", "2026-02", "2026-05"}


def test_roas_computed_from_attributed_revenue_over_fee(db):
    ev = _evidence(db)
    by_month = {c.month: c for c in ev.prior_performance}

    assert by_month["2025-09"].fee == 4000.0
    assert by_month["2025-09"].attributed_revenue == 9840.0
    assert by_month["2025-09"].attributed_roas == pytest.approx(9840 / 4000, abs=0.01)

    assert by_month["2026-02"].fee == 4000.0
    assert by_month["2026-02"].attributed_revenue == 10120.0
    assert by_month["2026-02"].attributed_roas == pytest.approx(10120 / 4000, abs=0.01)

    may = by_month["2026-05"]
    assert may.fee == 4200.0
    assert may.attributed_revenue == 31240.0
    assert may.attributed_roas == pytest.approx(31240 / 4200, abs=0.01)
    assert may.link_clicks == 385
    assert may.code_redemptions == 1847


def test_attribution_caution_remains_a_hypothesis(db):
    ev = _evidence(db)
    assert len(ev.measurement_cautions) >= 1
    caution = ev.measurement_cautions[0]
    assert caution.claim_class == "hypothesis"
    assert caution.status == "needs_review"
    assert "leakage" in caution.summary.lower() or "off-link" in caution.summary.lower()
    assert "not a confirmed" in caution.summary.lower()
    assert caution.code_redemptions == 1847
    assert caution.link_clicks == 385


def test_portfolio_evidence_marked_synthetic_with_seed_count(db):
    ev = _evidence(db)
    assert ev.portfolio_evidence is not None
    assert ev.portfolio_evidence.evidence_count == 31
    assert ev.portfolio_evidence.synthetic is True
    assert ev.portfolio_evidence.pattern_id == "pattern_hybrid_comp"


# ---- 2. memory lifecycle grounding ----

def test_superseded_strategy_excluded_new_strategy_included(db):
    candidates, _ = propose_candidates_from_message(
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
    approve_candidate(db, strategy_candidate)
    resolve_conflict(db, strategy_candidate, "SUPERSEDE")
    db.commit()

    ev = _evidence(db)
    values = {m.value for m in ev.client_memory}
    assert "reduce_coupon_dependence" in values
    assert "aggressively_grow_coupon_partnerships" not in values


# ---- 3. learning-loop freshness ----

def test_evidence_reflects_incremented_pattern_count_after_outcome(db):
    ev_before = _evidence(db)
    assert ev_before.portfolio_evidence.evidence_count == 31

    decision = Decision(
        client_id="northwind", partner_id="summit_sisters", decision_type="creator_renewal",
        summary="Renew Summit Sisters under hybrid compensation",
        terms={"base_fee": 3500, "performance_bonus_pct": 10, "bonus_basis": "verified_new_customer_revenue"},
        rationale="test", motivated_by_claim_ids=["pattern_hybrid_comp"], status="approved", synthetic=False,
    )
    db.add(decision)
    db.flush()
    db.add(Outcome(decision_id=decision.id, metrics={}, outcome_label="positive", is_simulated=True))
    pattern = db.get(PortfolioPattern, "pattern_hybrid_comp")
    execute_promote_pattern_evidence(db, pattern, positive=True, new_decision_id=decision.id)
    db.commit()

    ev_after = _evidence(db)
    assert ev_after.portfolio_evidence.evidence_count == 32
