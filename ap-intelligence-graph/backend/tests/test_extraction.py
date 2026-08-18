"""Tests for Step 1: hardened memory extraction.

Covers the specific failure mode found in the pre-launch audit - a live LLM
call phrasing the Northwind strategy update differently than expected and
missing the seeded-conflict SUPERSEDE - plus the new Pydantic validation and
unknown-predicate review path introduced to close it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config_module
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.memory import manager
from app.memory.predicates import normalize_predicate
from app.models import Client, MemoryCandidate, MemoryClaim


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(Client(id="northwind", name="Northwind Outfitters", synthetic=False))
    session.add(MemoryClaim(
        id="mem_northwind_strategy_coupon", type="client_preference", subject_type="client",
        subject_id="northwind", predicate="partnership_strategy", value="aggressively_grow_coupon_partnerships",
        scope={"client_id": "northwind"}, client_id="northwind", claim_class="verified_fact",
        confidence=0.9, authority_score=0.85, source={"type": "account_team_statement"},
        valid_from="2026-01-01", status="active", supersedes=[], synthetic=False,
    ))
    session.flush()
    yield session
    session.close()


def _patch_extractor(monkeypatch, claims: list[dict], provider_name: str = "test_stub"):
    monkeypatch.setattr(
        manager, "extract_candidate_claims",
        lambda message, client_id, client_name, known_predicates=None, known_partners=None: (claims, provider_name),
    )


def _claim(predicate: str, value: str, **overrides) -> dict:
    base = dict(
        type="client_preference", subject_type="client", subject_id="northwind",
        subject_label="Northwind Outfitters", predicate=predicate, value=value,
        claim_class="verified_fact", confidence=0.9,
    )
    base.update(overrides)
    return base


# ---- normalize_predicate unit tests ----

def test_canonical_predicate_is_recognized_as_is():
    normalized, is_known = normalize_predicate("partnership_strategy")
    assert normalized == "partnership_strategy"
    assert is_known is True


def test_alias_normalizes_to_canonical():
    normalized, is_known = normalize_predicate("client_strategy")
    assert normalized == "partnership_strategy"
    assert is_known is True


def test_unknown_predicate_is_left_unchanged():
    normalized, is_known = normalize_predicate("seasonal_campaign_focus")
    assert normalized == "seasonal_campaign_focus"
    assert is_known is False


# ---- pipeline tests ----

def test_partnership_strategy_conflict_detected(db, monkeypatch):
    _patch_extractor(monkeypatch, [_claim("partnership_strategy", "reduce_coupon_dependence", confidence=0.93)])
    candidates, _ = manager.propose_candidates_from_message(db, client_id="northwind", message="irrelevant")
    assert len(candidates) == 1
    c = candidates[0]
    assert c.claim_payload["predicate"] == "partnership_strategy"
    assert c.proposed_operation == "SUPERSEDE"
    assert c.conflict_with_claim_id == "mem_northwind_strategy_coupon"


def test_client_strategy_alias_still_triggers_supersede(db, monkeypatch):
    """Core Step-1 requirement: a semantically-equivalent but differently
    spelled predicate must not cause the conflict to be missed."""
    _patch_extractor(monkeypatch, [_claim("client_strategy", "reduce_coupon_dependence", confidence=0.93)])
    candidates, _ = manager.propose_candidates_from_message(db, client_id="northwind", message="irrelevant")
    assert len(candidates) == 1
    c = candidates[0]
    assert c.claim_payload["predicate"] == "partnership_strategy"  # normalized, not "client_strategy"
    assert c.proposed_operation == "SUPERSEDE"
    assert c.conflict_with_claim_id == "mem_northwind_strategy_coupon"


def test_primary_growth_objective_no_conflict_creates(db, monkeypatch):
    _patch_extractor(monkeypatch, [_claim("primary_growth_objective", "new_customer_acquisition", confidence=0.94)])
    candidates, _ = manager.propose_candidates_from_message(db, client_id="northwind", message="irrelevant")
    assert len(candidates) == 1
    c = candidates[0]
    assert c.claim_payload["predicate"] == "primary_growth_objective"
    assert c.proposed_operation == "CREATE"
    assert c.conflict_with_claim_id is None


def test_unknown_predicate_routes_to_human_review_without_coercion(db, monkeypatch):
    _patch_extractor(monkeypatch, [_claim("seasonal_campaign_focus", "holiday_push", claim_class="account_preference", confidence=0.7)])
    candidates, _ = manager.propose_candidates_from_message(db, client_id="northwind", message="irrelevant")
    assert len(candidates) == 1
    c = candidates[0]
    assert c.claim_payload["predicate"] == "seasonal_campaign_focus"  # not coerced
    assert c.proposed_operation == "REQUEST_HUMAN_REVIEW"
    assert c.conflict_with_claim_id is None


def test_malformed_extraction_is_dropped_not_persisted(db, monkeypatch):
    missing_predicate = {
        "type": "client_preference", "subject_type": "client", "subject_id": "northwind",
        "subject_label": "Northwind Outfitters", "value": "reduce_coupon_dependence",
        "claim_class": "verified_fact", "confidence": 0.93,
    }
    out_of_range_confidence = _claim("primary_growth_objective", "new_customer_acquisition", confidence=1.5)
    valid = _claim("accepts_tradeoff", "lower_short_term_roas", claim_class="account_preference", confidence=0.85)

    _patch_extractor(monkeypatch, [missing_predicate, out_of_range_confidence, valid])
    candidates, _ = manager.propose_candidates_from_message(db, client_id="northwind", message="irrelevant")

    assert len(candidates) == 1
    assert candidates[0].claim_payload["predicate"] == "accepts_tradeoff"
    assert db.query(MemoryCandidate).count() == 1


def test_exact_demo_sentence_via_mock_provider_yields_three_candidates_incl_supersede(db, monkeypatch):
    """Runs the real (deterministic) extraction path end-to-end against the
    exact Scene-2 sentence from PROJECT_AP_Intelligence_Graph.md, forced onto
    the mock provider so the test is network-independent regardless of
    whether OPENAI_API_KEY happens to be set in the environment."""
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)

    message = (
        "Northwind's strategy changed after last week's executive review. "
        "They now want to reduce coupon dependence and prioritize new-customer growth, "
        "even if short-term ROAS is a little lower."
    )
    candidates, provider_name = manager.propose_candidates_from_message(db, client_id="northwind", message=message)

    assert provider_name == "mock_deterministic"
    assert len(candidates) == 3
    by_predicate = {c.claim_payload["predicate"]: c for c in candidates}
    assert set(by_predicate) == {"partnership_strategy", "primary_growth_objective", "accepts_tradeoff"}

    strategy_candidate = by_predicate["partnership_strategy"]
    assert strategy_candidate.proposed_operation == "SUPERSEDE"
    assert strategy_candidate.conflict_with_claim_id == "mem_northwind_strategy_coupon"
    assert strategy_candidate.claim_payload["value"] == "reduce_coupon_dependence"
