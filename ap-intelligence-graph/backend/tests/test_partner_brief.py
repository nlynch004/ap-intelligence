"""Tests for Phase 3: Partner Brief.

Covers deterministic PartnerBriefEvidence assembly (Summit Sisters'
real-data numbers, active-only client-memory filtering, per-partner
campaign isolation, synthetic flags, decision/outcome freshness) and the
mock provider's rule-based brief (forced deterministic - no
OPENAI_API_KEY, same bar as the rest of this suite) plus its safe fallback
on malformed live output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config_module
import app.llm.factory as factory
import app.seed as seed_module
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.partner_brief_agent import generate_partner_brief
from app.llm.provider import LLMProvider
from app.memory import manager
from app.memory.manager import approve_candidate, resolve_conflict, run_partner_brief
from app.memory.retrieval import build_partner_brief_context
from app.models import Decision, MemoryCandidate, Outcome


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_partner_brief.db"
    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(seed_module, "engine", engine)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)  # force deterministic mock

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    seed_module.seed(session, reset=True)
    yield session
    session.close()


# ---- Summit Sisters: deterministic evidence accuracy ----

def test_summit_sisters_evidence_has_exactly_its_three_campaigns(db):
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    ev = ctx["evidence"]
    assert ev.performance_stats.campaign_count == 3
    assert {c.campaign_id for c in ev.campaigns} == {"camp_summit_2025_09", "camp_summit_2026_02", "camp_summit_2026_05"}


def test_summit_sisters_may_roas_and_average_are_computed_correctly(db):
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    stats = ctx["evidence"].performance_stats
    may = next(c for c in ctx["evidence"].campaigns if c.campaign_id == "camp_summit_2026_05")
    assert may.attributed_roas == 7.44
    assert stats.most_recent_roas == 7.44
    expected_avg = round((2.46 + 2.53 + 7.44) / 3, 2)
    assert stats.average_roas == expected_avg


def test_summit_sisters_attribution_hypothesis_visible_and_not_upgraded(db):
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    cautions = ctx["evidence"].measurement_cautions
    assert len(cautions) == 1
    assert cautions[0].claim_class == "hypothesis"
    assert cautions[0].status == "needs_review"
    assert "not a confirmed" in cautions[0].summary.lower()
    assert "confirmed leakage" not in cautions[0].summary.lower()


def test_jessica_moreno_worked_with_and_negotiation_history_both_present(db):
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    ev = ctx["evidence"]
    assert any(t.team_member_id == "jessica_moreno" and t.worked_with for t in ev.team_experience)
    assert any(h.predicate == "negotiation_history" for h in ev.relationship_history)


def test_summit_sisters_is_not_marked_synthetic(db):
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    assert ctx["evidence"].partner.synthetic is False


def test_current_client_strategy_appears(db):
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    predicates = {c.predicate for c in ctx["evidence"].client_context}
    assert "partnership_strategy" in predicates
    strategy = next(c for c in ctx["evidence"].client_context if c.predicate == "partnership_strategy")
    assert strategy.value == "aggressively_grow_coupon_partnerships"  # the seeded, still-active belief


def test_superseded_strategy_excluded_after_supersede(db):
    # Run the exact Step-2 scripted supersede, then confirm the OLD belief
    # no longer appears in client_context as though it were current.
    candidates, _ = manager.propose_candidates_from_message(
        db, client_id="northwind",
        message=(
            "Northwind's strategy changed after last week's executive review. They now want to "
            "reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS "
            "is a little lower."
        ),
    )
    strategy_candidate = next(c for c in candidates if c.claim_payload["predicate"] == "partnership_strategy")
    resolve_conflict(db, strategy_candidate, "SUPERSEDE")
    for c in candidates:
        if c.id != strategy_candidate.id:
            approve_candidate(db, c)
    db.commit()

    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    values = {c.value for c in ctx["evidence"].client_context}
    assert "aggressively_grow_coupon_partnerships" not in values
    assert "reduce_coupon_dependence" in values


def test_unknown_partner_returns_none(db):
    assert build_partner_brief_context(db, partner_id="does_not_exist", client_id="northwind") is None


# ---- per-archetype campaign isolation + synthetic flags ----

def test_peak_pursuit_campaigns_isolated_and_synthetic(db):
    ctx = build_partner_brief_context(db, partner_id="peak_pursuit", client_id="northwind")
    ev = ctx["evidence"]
    assert ev.performance_stats.campaign_count == 3
    assert {c.campaign_id for c in ev.campaigns} == {"camp_peak_2025_11", "camp_peak_2026_02", "camp_peak_2026_05"}
    assert ev.partner.synthetic is True
    assert ev.measurement_cautions == []  # no fabricated caution
    assert ev.performance_stats.average_roas >= 3.0  # strong archetype


def test_campfire_kate_campaigns_isolated(db):
    ctx = build_partner_brief_context(db, partner_id="campfire_kate", client_id="northwind")
    ev = ctx["evidence"]
    assert ev.performance_stats.campaign_count == 2
    assert {c.campaign_id for c in ev.campaigns} == {"camp_kate_2026_02", "camp_kate_2026_05"}
    assert 1.5 <= ev.performance_stats.average_roas < 3.0  # moderate archetype
    assert ev.measurement_cautions == []
    assert ev.partner.partner_note is not None and "first-time buyers" in ev.partner.partner_note
    # The audience-fit note is structured source data, not governed memory,
    # unless a lesson has actually been approved.
    assert ev.relationship_history == []


def test_backcountry_ben_weak_economics_clean_measurement(db):
    ctx = build_partner_brief_context(db, partner_id="backcountry_ben", client_id="northwind")
    ev = ctx["evidence"]
    assert ev.performance_stats.campaign_count == 2
    assert {c.campaign_id for c in ev.campaigns} == {"camp_ben_2025_12", "camp_ben_2026_04"}
    assert ev.performance_stats.average_roas < 1.5  # weak archetype
    assert ev.measurement_cautions == []
    # High engagement despite weak commerce - the exact tension this
    # archetype exists to test (spec Phase 3 Sec.12).
    assert ev.performance_stats.average_engagement_rate > 0.08
    for c in ev.campaigns:
        assert c.impressions is not None and c.engagements is not None


# ---- decision/outcome freshness ----

def test_no_prior_decision_for_summit_sisters_before_scripted_flow(db):
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    assert ctx["evidence"].prior_decisions == []
    assert ctx["evidence"].outcomes == []


def test_decision_and_simulated_outcome_appear_once_created(db):
    decision = Decision(
        client_id="northwind", partner_id="summit_sisters", decision_type="creator_renewal",
        summary="renew_with_hybrid_compensation",
        terms={"base_fee": 4200, "performance_bonus_pct": 20, "bonus_basis": "verified_new_customer_revenue"},
        rationale="test", motivated_by_claim_ids=[], status="approved", synthetic=False,
    )
    db.add(decision)
    db.flush()
    outcome = Outcome(
        decision_id=decision.id, metrics={"verified_new_customer_revenue": 23700, "attributed_revenue": 32600},
        outcome_label="positive", is_simulated=True,
    )
    db.add(outcome)
    db.commit()

    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    ev = ctx["evidence"]
    assert len(ev.prior_decisions) == 1
    assert ev.prior_decisions[0].decision_id == decision.id
    assert ev.prior_decisions[0].terms["base_fee"] == 4200
    assert len(ev.outcomes) == 1
    assert ev.outcomes[0].is_simulated is True
    assert ev.outcomes[0].outcome_label == "positive"


# ---- run_partner_brief (LLM layer via mock) ----

def test_run_partner_brief_summit_sisters_prose_reflects_evidence(db):
    brief = run_partner_brief(db, partner_id="summit_sisters", client_id="northwind")
    assert brief is not None
    assert "not a confirmed" in " ".join(brief.measurement_considerations).lower() or any(
        "not a confirmed" in c.summary.lower() for c in brief.evidence.measurement_cautions
    )
    assert "jessica moreno" in brief.relationship_summary.lower()
    assert "worked with" in brief.relationship_summary.lower()


def test_run_partner_brief_peak_pursuit_reflects_no_lesson_before_approval(db):
    brief = run_partner_brief(db, partner_id="peak_pursuit", client_id="northwind")
    assert brief is not None
    assert brief.evidence.relationship_history == []  # Phase 2 lesson not yet approved


def test_run_partner_brief_reflects_approved_phase2_lesson(db):
    # Approve a Phase-2 campaign-review lesson for Peak Pursuit, then
    # confirm the brief now truthfully includes it - not hardcoded.
    from app.memory.manager import run_campaign_review

    review = run_campaign_review(db, campaign_id="camp_peak_2026_05")
    lesson_out = next(c for c in review.candidate_lessons if c.claim_payload.predicate == "partner_performance_pattern")
    approve_candidate(db, db.get(MemoryCandidate, lesson_out.id))
    db.commit()

    brief = run_partner_brief(db, partner_id="peak_pursuit", client_id="northwind")
    assert any(h.predicate == "partner_performance_pattern" for h in brief.evidence.relationship_history)


def test_unknown_partner_via_run_partner_brief_returns_none(db):
    assert run_partner_brief(db, partner_id="does_not_exist", client_id="northwind") is None


# ---- malformed live output falls back safely (call_with_fallback reuse) ----

class _BrokenPartnerBriefProvider(LLMProvider):
    name = "broken_partner_brief_test_provider"

    def extract_claims(self, *a, **k):
        raise NotImplementedError

    def recommend(self, *a, **k):
        raise NotImplementedError

    def summarize(self, *a, **k):
        raise NotImplementedError

    def review_campaign(self, *a, **k):
        raise NotImplementedError

    def summarize_history(self, *a, **k):
        raise NotImplementedError

    def compare_scenarios(self, *a, **k):
        raise NotImplementedError

    def propose_plan(self, *a, **k):
        raise NotImplementedError

    def generate_partner_brief(self, evidence):
        return {"relationship_summary": "ok"}  # missing required performance_summary


def test_malformed_partner_brief_output_falls_back_to_mock(monkeypatch, db):
    monkeypatch.setattr(factory, "get_provider", lambda: _BrokenPartnerBriefProvider())
    ctx = build_partner_brief_context(db, partner_id="summit_sisters", client_id="northwind")
    result, provider_name = generate_partner_brief(ctx["evidence"].model_dump())
    assert provider_name.endswith("(fallback)")
    assert result["performance_summary"]  # present and non-blank, from the mock
