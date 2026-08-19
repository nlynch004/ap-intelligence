"""Tests for Phase 4: Historical "What Changed?" Retrieval.

Covers the deterministic HistoricalMemoryTimeline (chronological ordering,
version-chain integrity across a 3-version chain, generic predicate/subject
support, provenance/confidence preservation), current-state isolation
(active_client_memories and every other current-state workflow must keep
excluding superseded history), read-only guarantees, and the mock
provider's safe-fallback narration.
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

from app.agents.memory_history_agent import generate_historical_summary
from app.llm.provider import LLMProvider
from app.memory.manager import (
    approve_candidate,
    reject_candidate,
    resolve_conflict,
    run_campaign_review,
    run_memory_history,
    run_partner_brief,
    run_what_changed_summary,
)
from app.memory.operations import execute_create, execute_supersede
from app.memory.retrieval import (
    active_client_memories,
    active_partner_memories,
    build_campaign_review_context,
    build_memory_history,
    build_recommendation_context,
    resolve_historical_predicate,
)
from app.models import MemoryCandidate, MemoryClaim


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_memory_history.db"
    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(seed_module, "engine", engine)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)  # force deterministic mock

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    seed_module.seed(session, reset=True)
    yield session
    session.close()


def _supersede_strategy(db, new_value: str, message_excerpt: str = "") -> tuple[MemoryClaim, MemoryClaim]:
    """Helper mirroring the real chat-extraction -> approve -> SUPERSEDE
    pipeline, but driving execute_supersede directly for deterministic,
    fast test setup of multi-version chains (Phase 4 doesn't need to
    re-test extraction itself - that's covered elsewhere)."""
    existing = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.subject_type == "client", MemoryClaim.subject_id == "northwind",
                MemoryClaim.predicate == "partnership_strategy", MemoryClaim.status == "active")
        .one()
    )
    payload = {
        "type": "client_preference", "subject_type": "client", "subject_id": "northwind",
        "subject_label": "Northwind Outfitters", "predicate": "partnership_strategy", "value": new_value,
        "claim_class": "verified_fact", "confidence": 0.95,
    }
    source = {"type": "account_team_statement", "source_id": "test", "speaker": "account_manager", "message_excerpt": message_excerpt}
    new_claim, old_claim = execute_supersede(db, existing, payload, client_id="northwind", source=source)
    db.commit()
    return new_claim, old_claim


# ---- basic two-version history ----

def test_basic_strategy_history_old_superseded_new_active(db):
    _supersede_strategy(db, "reduce_coupon_dependence", "after last week's executive review")
    result = build_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    assert result is not None
    entries = result["entries"]
    assert len(entries) == 2
    assert entries[0].value == "aggressively_grow_coupon_partnerships"
    assert entries[0].status == "superseded"
    assert entries[1].value == "reduce_coupon_dependence"
    assert entries[1].status == "active"
    assert result["current_claim_id"] == entries[1].claim_id


# ---- three-version chain ----

def test_three_version_chain_ordering_and_status(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    _supersede_strategy(db, "prioritize_high_intent_creator_partnerships")

    result = build_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    entries = result["entries"]
    assert len(entries) == 3
    values = [e.value for e in entries]
    assert values == [
        "aggressively_grow_coupon_partnerships",
        "reduce_coupon_dependence",
        "prioritize_high_intent_creator_partnerships",
    ]
    statuses = [e.status for e in entries]
    assert statuses == ["superseded", "superseded", "active"]
    # Version-chain pointers, not just values - each entry's supersedes/
    # superseded_by should chain correctly.
    assert entries[0].superseded_by == entries[1].claim_id
    assert entries[1].supersedes == [entries[0].claim_id]
    assert entries[1].superseded_by == entries[2].claim_id
    assert entries[2].supersedes == [entries[1].claim_id]
    assert result["current_claim_id"] == entries[2].claim_id


def test_timeline_ordering_is_deterministic_valid_from_then_created_at(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    _supersede_strategy(db, "prioritize_high_intent_creator_partnerships")
    result = build_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    entries = result["entries"]
    valid_froms = [e.valid_from for e in entries]
    assert valid_froms == sorted(valid_froms)


# ---- generic predicate + subject support ----

def test_growth_objective_history_is_generic_not_hardcoded(db):
    existing = execute_create(
        db,
        {"type": "client_preference", "subject_type": "client", "subject_id": "northwind", "subject_label": "Northwind Outfitters",
         "predicate": "primary_growth_objective", "value": "new_customer_acquisition", "claim_class": "verified_fact", "confidence": 0.9},
        client_id="northwind", source={"type": "account_team_statement"},
    )
    execute_supersede(
        db, existing,
        {"type": "client_preference", "subject_type": "client", "subject_id": "northwind", "subject_label": "Northwind Outfitters",
         "predicate": "primary_growth_objective", "value": "repeat_purchase_growth", "claim_class": "verified_fact", "confidence": 0.9},
        client_id="northwind", source={"type": "account_team_statement"},
    )
    db.commit()

    result = build_memory_history(db, subject_type="client", subject_id="northwind", predicate="primary_growth_objective")
    assert result is not None
    values = [e.value for e in result["entries"]]
    assert values == ["new_customer_acquisition", "repeat_purchase_growth"]
    assert result["entries"][0].status == "superseded"
    assert result["entries"][1].status == "active"


def test_partner_scoped_history_via_campaign_review_lesson(db):
    review = run_campaign_review(db, campaign_id="camp_peak_2026_05")
    lesson = next(c for c in review.candidate_lessons if c.claim_payload.predicate == "partner_performance_pattern")
    candidate = db.get(MemoryCandidate, lesson.id)
    result1 = approve_candidate(db, candidate)
    db.commit()

    # Create a second version via a fresh candidate that conflicts with it.
    payload = {
        "type": "relationship_memory", "subject_type": "creator", "subject_id": "peak_pursuit",
        "subject_label": "Peak Pursuit", "predicate": "partner_performance_pattern",
        "value": "renewal_economics_under_review", "claim_class": "historical_observation", "confidence": 0.7,
    }
    execute_supersede(db, result1["claim"], payload, client_id="northwind", source={"type": "agent_inference"})
    db.commit()

    result = build_memory_history(db, subject_type="creator", subject_id="peak_pursuit", predicate="partner_performance_pattern")
    assert result is not None
    assert len(result["entries"]) == 2
    assert result["entries"][0].status == "superseded"
    assert result["entries"][1].status == "active"
    assert result["subject_name"] == "Peak Pursuit"


# ---- provenance + confidence/authority preservation ----

def test_source_confidence_authority_preserved_in_timeline(db):
    _supersede_strategy(db, "reduce_coupon_dependence", "after last week's executive review")
    result = build_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    new_entry = result["entries"][1]
    assert new_entry.confidence == 0.95
    assert new_entry.source.get("message_excerpt") == "after last week's executive review"
    old_entry = result["entries"][0]
    assert old_entry.confidence == 0.9  # unchanged from seed
    assert old_entry.authority_score == 0.85  # unchanged from seed


# ---- ordering / empty-state / no-fabrication ----

def test_single_claim_is_not_fabricated_as_change(db):
    result = build_memory_history(db, subject_type="creator", subject_id="campfire_kate", predicate="relationship_status")
    assert result is None  # Campfire Kate has zero governed memory claims (Phase 1 design)


def test_unknown_subject_predicate_returns_none(db):
    assert build_memory_history(db, subject_type="client", subject_id="northwind", predicate="does_not_exist") is None


def test_rejected_status_never_surfaces(db):
    # No MemoryClaim ever reaches "rejected" in current code, but the
    # filter itself must exist and not accidentally exclude valid history.
    _supersede_strategy(db, "reduce_coupon_dependence")
    result = build_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    assert all(e.status != "rejected" for e in result["entries"])


# ---- current-state isolation (the most important regression) ----

def test_active_client_memories_excludes_superseded_after_three_versions(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    _supersede_strategy(db, "prioritize_high_intent_creator_partnerships")
    active = active_client_memories(db, "northwind")
    strategy_claims = [c for c in active if c.predicate == "partnership_strategy"]
    assert len(strategy_claims) == 1
    assert strategy_claims[0].value == "prioritize_high_intent_creator_partnerships"


def test_partner_brief_current_context_isolated_from_history(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    _supersede_strategy(db, "prioritize_high_intent_creator_partnerships")
    brief = run_partner_brief(db, partner_id="summit_sisters", client_id="northwind")
    values = {c.value for c in brief.evidence.client_context}
    assert values == {"prioritize_high_intent_creator_partnerships"}
    assert "aggressively_grow_coupon_partnerships" not in values
    assert "reduce_coupon_dependence" not in values


def test_campaign_review_current_context_isolated_from_history(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    _supersede_strategy(db, "prioritize_high_intent_creator_partnerships")
    ctx = build_campaign_review_context(db, campaign_id="camp_summit_2026_05")
    values = {c.value for c in ctx["evidence"].client_memory}
    assert "aggressively_grow_coupon_partnerships" not in values
    assert "reduce_coupon_dependence" not in values


def test_recommendation_decision_evidence_isolated_from_history(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    _supersede_strategy(db, "prioritize_high_intent_creator_partnerships")
    ctx = build_recommendation_context(db, client_id="northwind", partner_id="summit_sisters", question="Should we renew Summit Sisters?")
    values = {c.value for c in ctx["decision_evidence"].client_memory}
    assert "aggressively_grow_coupon_partnerships" not in values
    assert "reduce_coupon_dependence" not in values
    assert "prioritize_high_intent_creator_partnerships" in values


# ---- read-only guarantee ----

def test_historical_retrieval_produces_no_mutations(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    claims_before = db.query(MemoryClaim).count()
    candidates_before = db.query(MemoryCandidate).count()

    build_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    run_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    run_what_changed_summary(db, subject_type="client", subject_id="northwind")

    assert db.query(MemoryClaim).count() == claims_before
    assert db.query(MemoryCandidate).count() == candidates_before


# ---- what-changed broad summary ----

def test_what_changed_summary_finds_real_version_history_only(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    summary = run_what_changed_summary(db, subject_type="client", subject_id="northwind")
    predicates = {d.predicate for d in summary.changed_dimensions}
    assert "partnership_strategy" in predicates
    strategy_dim = next(d for d in summary.changed_dimensions if d.predicate == "partnership_strategy")
    assert strategy_dim.old_value == "aggressively_grow_coupon_partnerships"
    assert strategy_dim.new_value == "reduce_coupon_dependence"


def test_what_changed_summary_empty_when_nothing_changed(db):
    summary = run_what_changed_summary(db, subject_type="creator", subject_id="campfire_kate", client_id="northwind")
    assert summary.changed_dimensions == []


# ---- run_memory_history / mock narration ----

def test_run_memory_history_narrates_without_inventing_reason(db):
    _supersede_strategy(db, "reduce_coupon_dependence")  # no message_excerpt given
    result = run_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    assert result is not None
    joined = " ".join(result.historical_context).lower()
    assert "reason not captured" in joined or "source" in joined
    assert result.summary  # non-empty


def test_run_memory_history_cites_genuine_source_context(db):
    _supersede_strategy(db, "reduce_coupon_dependence", "after last week's executive review")
    result = run_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    joined = " ".join(result.historical_context)
    assert "executive review" in joined


def test_run_memory_history_single_entry_no_fabricated_evolution(db):
    result = run_memory_history(db, subject_type="creator", subject_id="summit_sisters", predicate="relationship_status")
    assert result is not None
    assert len(result.timeline.changes) == 1
    assert result.material_changes == []
    assert "no governed change history" in result.summary.lower()


def test_run_memory_history_unknown_returns_none(db):
    assert run_memory_history(db, subject_type="client", subject_id="northwind", predicate="does_not_exist") is None


# ---- resolve_historical_predicate (deterministic keyword matching) ----

def test_resolve_historical_predicate_matches_known_phrases():
    assert resolve_historical_predicate("How has Northwind's partnership strategy changed?") == "partnership_strategy"
    assert resolve_historical_predicate("What changed in Northwind's growth objective?") == "primary_growth_objective"
    assert resolve_historical_predicate("Why did Northwind stop prioritizing coupon growth?") == "partnership_strategy"
    assert resolve_historical_predicate("How has our view of Summit Sisters changed?") is None


# ---- malformed live output falls back safely (same call_with_fallback pattern) ----

class _BrokenHistoryProvider(LLMProvider):
    name = "broken_history_test_provider"

    def extract_claims(self, *a, **k):
        raise NotImplementedError

    def recommend(self, *a, **k):
        raise NotImplementedError

    def summarize(self, *a, **k):
        raise NotImplementedError

    def review_campaign(self, *a, **k):
        raise NotImplementedError

    def generate_partner_brief(self, *a, **k):
        raise NotImplementedError

    def compare_scenarios(self, *a, **k):
        raise NotImplementedError

    def propose_plan(self, *a, **k):
        raise NotImplementedError

    def summarize_history(self, evidence):
        return {"summary": 12345}  # wrong type - should be a string


def test_malformed_historical_summary_falls_back_to_mock(monkeypatch, db):
    monkeypatch.setattr(factory, "get_provider", lambda: _BrokenHistoryProvider())
    _supersede_strategy(db, "reduce_coupon_dependence")
    result = build_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    raw, provider_name = generate_historical_summary({
        "subject_name": result["subject_name"], "predicate": "partnership_strategy",
        "current_claim_id": result["current_claim_id"], "entries": [e.model_dump() for e in result["entries"]],
    })
    assert provider_name.endswith("(fallback)")
    assert isinstance(raw["summary"], str) and raw["summary"]
