"""Tests for Phase 2: Campaign Review.

Covers the three required archetypes (Summit Sisters/attribution caution,
Peak Pursuit/clean strong economics, Campfire Kate/moderate + strategic-fit
metadata), the deterministic CampaignReviewEvidence assembly, the mock
provider's rule-based review (forced deterministic - no OPENAI_API_KEY, same
"genuinely demoable with zero API calls" bar as the rest of this suite), and
the memory-candidate pipeline reuse (approve/reject/REQUEST_HUMAN_REVIEW,
same governed path chat extraction uses).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config_module
import app.seed as seed_module
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.memory.manager import approve_candidate, reject_candidate, run_campaign_review
from app.memory.retrieval import build_campaign_review_context
from app.models import MemoryCandidate, MemoryClaim


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_campaign_review.db"
    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(seed_module, "engine", engine)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)  # force deterministic mock

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    seed_module.seed(session, reset=True)
    yield session
    session.close()


# ---- deterministic evidence assembly ----

def test_summit_sisters_evidence_numbers_are_exact(db):
    ctx = build_campaign_review_context(db, campaign_id="camp_summit_2026_05")
    ev = ctx["evidence"]
    assert ev.partner_name == "Summit Sisters"
    assert ev.attributed_roas == 7.44
    assert ev.link_clicks == 385
    assert ev.code_redemptions == 1847
    assert ev.attributed_revenue == 31240.0
    assert ev.fee == 4200.0
    assert ev.synthetic is False
    # The attribution hypothesis must surface as a measurement caution, still
    # a hypothesis / needs_review - never silently dropped, never upgraded.
    assert len(ev.measurement_cautions) == 1
    caution = ev.measurement_cautions[0]
    assert caution.claim_class == "hypothesis"
    assert caution.status == "needs_review"
    assert "not a confirmed" in caution.summary.lower()


def test_prior_campaign_comparison_is_computed_not_guessed(db):
    ctx = build_campaign_review_context(db, campaign_id="camp_summit_2026_05")
    comparison = ctx["evidence"].prior_campaign_comparison
    assert comparison.has_prior is True
    assert comparison.prior_month_label == "February 2026"
    # fee: 4200 - 4000 = 200; revenue: 31240 - 10120 = 21120
    assert comparison.fee_delta == 200.0
    assert comparison.revenue_delta == 21120.0
    assert comparison.roas_delta == round(7.44 - 2.53, 2)


def test_first_campaign_has_no_prior_comparison(db):
    ctx = build_campaign_review_context(db, campaign_id="camp_summit_2025_09")
    assert ctx["evidence"].prior_campaign_comparison.has_prior is False


def test_partner_note_carried_as_observed_metadata_not_memory(db):
    ctx = build_campaign_review_context(db, campaign_id="camp_kate_2026_05")
    ev = ctx["evidence"]
    assert ev.partner_note is not None
    assert "first-time buyers" in ev.partner_note
    # Not itself a governed claim - Campfire Kate has zero seeded memory_claims.
    assert ev.partner_memory == []


def test_unknown_campaign_returns_none(db):
    assert build_campaign_review_context(db, campaign_id="does_not_exist") is None


# ---- archetype A: Summit Sisters (attribution caution must stay a hypothesis) ----

def test_archetype_a_summit_sisters_review(db):
    review = run_campaign_review(db, campaign_id="camp_summit_2026_05")
    assert review is not None
    assert review.evidence.attributed_roas == 7.44

    joined_uncertain = " ".join(review.what_is_uncertain).lower()
    assert "unverified" in joined_uncertain
    # The caution's own text explicitly disclaims certainty ("not a
    # confirmed attribution failure") - it must never read as a bare,
    # undisclaimed confirmation.
    assert "is a confirmed" not in joined_uncertain
    assert "confirmed leakage" not in joined_uncertain

    # The measurement caution stays exactly what it was - never upgraded.
    caution_claim = db.get(MemoryClaim, "mem_camp_summit_2026_05_attribution_risk")
    assert caution_claim.claim_class == "hypothesis"
    assert caution_claim.status == "needs_review"

    # The disputed ROAS must not be laundered into a stronger-sounding
    # governed partner-performance claim while the caution is open.
    lesson_predicates = {c.claim_payload.predicate for c in review.candidate_lessons}
    assert "partner_performance_pattern" not in lesson_predicates


# ---- archetype B: Peak Pursuit (strong, clean - economics/renewal framing) ----

def test_archetype_b_peak_pursuit_review(db):
    review = run_campaign_review(db, campaign_id="camp_peak_2026_05")
    assert review is not None
    assert review.evidence.measurement_cautions == []
    assert review.evidence.attributed_roas == 4.91

    joined_implications = " ".join(review.planning_implications).lower()
    assert "price" in joined_implications or "renewal" in joined_implications or "invest" in joined_implications

    # No attribution-risk claim may be fabricated for a campaign with no
    # leakage signal (clicks/redemptions ratio well under the seed threshold).
    lesson_predicates = {c.claim_payload.predicate for c in review.candidate_lessons}
    assert "attribution_integrity_risk" not in lesson_predicates
    assert "partner_performance_pattern" in lesson_predicates
    strong_lesson = next(c for c in review.candidate_lessons if c.claim_payload.predicate == "partner_performance_pattern")
    assert strong_lesson.claim_payload.subject_type == "creator"
    assert strong_lesson.claim_payload.subject_id == "peak_pursuit"
    assert strong_lesson.proposed_operation == "CREATE"


# ---- archetype C: Campfire Kate (moderate commerce, strategic-fit metadata) ----

def test_archetype_c_campfire_kate_review(db):
    review = run_campaign_review(db, campaign_id="camp_kate_2026_05")
    assert review is not None
    assert 1.5 <= review.evidence.attributed_roas < 3.0  # moderate tier

    # Strategic-fit note may inform interpretation (shows up in prose)...
    joined = " ".join(review.what_is_uncertain + review.planning_implications).lower()
    assert "first-time" in joined or "strategic fit" in joined

    # ...but is never automatically promoted into governed memory: any
    # lesson referencing it is a human-reviewable candidate, not an active
    # claim, and moderate commerce alone does not trigger the
    # partner_performance_pattern (strong/weak only) lesson.
    predicates = {c.claim_payload.predicate for c in review.candidate_lessons}
    assert "partner_performance_pattern" not in predicates
    for lesson in review.candidate_lessons:
        assert lesson.status == "pending"  # proposed, not yet approved/persisted


# ---- memory behavior: the governed candidate pipeline ----

def test_unknown_lesson_predicate_routes_to_request_human_review(db):
    review = run_campaign_review(db, campaign_id="camp_kate_2026_05")
    audience_fit = next((c for c in review.candidate_lessons if c.claim_payload.predicate == "audience_fit"), None)
    assert audience_fit is not None, "expected the mock provider's deliberately-unknown audience_fit lesson"
    assert audience_fit.proposed_operation == "REQUEST_HUMAN_REVIEW"
    assert audience_fit.conflict_with_claim_id is None


def test_approved_candidate_lesson_becomes_a_real_claim(db):
    review = run_campaign_review(db, campaign_id="camp_peak_2026_05")
    lesson_out = next(c for c in review.candidate_lessons if c.claim_payload.predicate == "partner_performance_pattern")
    candidate = db.get(MemoryCandidate, lesson_out.id)
    assert candidate.origin == "campaign_review"
    assert candidate.origin_detail.get("campaign_id") == "camp_peak_2026_05"

    result = approve_candidate(db, candidate)
    assert result["operation_executed"] == "CREATE"
    claim = result["claim"]
    assert claim is not None
    assert claim.subject_type == "creator"
    assert claim.subject_id == "peak_pursuit"
    assert claim.predicate == "partner_performance_pattern"
    assert claim.status == "active"
    # Provenance stays explicit: model-derived, not account-team-stated.
    assert claim.source["type"] == "agent_inference"
    assert claim.source["campaign_id"] == "camp_peak_2026_05"

    # Now reachable as a real governed claim via the normal retrieval path.
    from app.memory.retrieval import active_partner_memories
    partner_claims = active_partner_memories(db, "peak_pursuit")
    assert any(c.id == claim.id for c in partner_claims)


def test_rejected_candidate_lesson_does_not_persist(db):
    review = run_campaign_review(db, campaign_id="camp_peak_2026_05")
    lesson_out = next(c for c in review.candidate_lessons if c.claim_payload.predicate == "partner_performance_pattern")
    candidate = db.get(MemoryCandidate, lesson_out.id)

    before = db.query(MemoryClaim).count()
    reject_candidate(db, candidate)
    after = db.query(MemoryClaim).count()

    assert after == before
    assert candidate.status == "rejected"
    from app.memory.retrieval import active_partner_memories
    assert active_partner_memories(db, "peak_pursuit") == []


def test_reset_restores_canonical_seed_state_after_campaign_review(db):
    run_campaign_review(db, campaign_id="camp_peak_2026_05")
    review = run_campaign_review(db, campaign_id="camp_kate_2026_05")
    lesson_out = next(c for c in review.candidate_lessons if c.claim_payload.predicate == "audience_fit")
    approve_candidate(db, db.get(MemoryCandidate, lesson_out.id))
    db.commit()

    baseline_claims = db.query(MemoryClaim).count()
    baseline_candidates = db.query(MemoryCandidate).count()
    assert baseline_candidates > 0  # sanity: state really is dirty

    seed_module.seed(db, reset=True)

    assert db.query(MemoryCandidate).count() == 0
    # Exactly the Phase-1 seeded claim count - no campaign-review artifacts survive a reset.
    assert db.query(MemoryClaim).count() == 18
    assert baseline_claims >= 18  # the dirtied state had at least the approved lesson on top


# ---- predicate vocabulary reuse ----

def test_partner_performance_pattern_alias_normalizes(db):
    from app.memory.predicates import normalize_predicate

    normalized, is_known = normalize_predicate("performance_characterization")
    assert normalized == "partner_performance_pattern"
    assert is_known is True


def test_canonical_partner_performance_pattern_recognized(db):
    from app.memory.predicates import normalize_predicate

    normalized, is_known = normalize_predicate("partner_performance_pattern")
    assert normalized == "partner_performance_pattern"
    assert is_known is True
