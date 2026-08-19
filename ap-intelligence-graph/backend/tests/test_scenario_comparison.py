"""Tests for Phase 5: Scenario Comparison.

Covers deterministic scenario construction (app.memory.scenario_rules),
the deterministic ScenarioComparisonEvidence assembly (Summit Sisters'
exact worked numbers, Peak Pursuit/Campfire Kate/Backcountry Ben
archetype differentiation), current-state isolation from Historical
Retrieval, the invented-scenario-id / malformed-output safe-fallback
behavior, and the read-only guarantee.
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

from app.agents.scenario_comparison_agent import generate_scenario_comparison
from app.llm.provider import LLMProvider
from app.memory import scenario_rules
from app.memory.manager import approve_candidate, resolve_conflict, run_memory_history, run_scenario_comparison
from app.memory.retrieval import build_memory_history, build_scenario_comparison_context
from app.models import Decision, MemoryCandidate, MemoryClaim, Outcome, PortfolioPattern


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_scenario_comparison.db"
    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(seed_module, "engine", engine)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)  # force deterministic mock

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    seed_module.seed(session, reset=True)
    yield session
    session.close()


def _supersede_strategy(db, new_value: str) -> None:
    existing = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.subject_type == "client", MemoryClaim.subject_id == "northwind",
                MemoryClaim.predicate == "partnership_strategy", MemoryClaim.status == "active")
        .one()
    )
    from app.memory.operations import execute_supersede
    payload = {
        "type": "client_preference", "subject_type": "client", "subject_id": "northwind",
        "subject_label": "Northwind Outfitters", "predicate": "partnership_strategy", "value": new_value,
        "claim_class": "verified_fact", "confidence": 0.95,
    }
    execute_supersede(db, existing, payload, client_id="northwind", source={"type": "account_team_statement"})
    db.commit()


# ---- pure scenario_rules unit tests ----

def test_build_scenarios_generic_shape():
    scenarios = scenario_rules.build_scenarios(latest_fee=4200.0, current_ask=6000.0)
    ids = {s["id"] for s in scenarios}
    assert ids == {"flat", "hybrid", "do_not_renew"}
    flat = next(s for s in scenarios if s["id"] == "flat")
    assert flat["base_fee"] == 6000.0
    hybrid = next(s for s in scenarios if s["id"] == "hybrid")
    assert hybrid["base_fee"] == 4200.0  # most recent campaign fee, NOT the ask
    assert hybrid["performance_bonus_pct"] == scenario_rules.HYBRID_DEFAULT_BONUS_PCT
    assert hybrid["bonus_basis"] == "verified_new_customer_revenue"
    no_renew = next(s for s in scenarios if s["id"] == "do_not_renew")
    assert no_renew["base_fee"] == 0.0
    assert no_renew["renews_relationship"] is False


def test_hybrid_falls_back_to_ask_when_no_campaign_history():
    scenarios = scenario_rules.build_scenarios(latest_fee=None, current_ask=5000.0)
    hybrid = next(s for s in scenarios if s["id"] == "hybrid")
    assert hybrid["base_fee"] == 5000.0


def test_summit_sisters_worked_example_matches_spec_exactly():
    """spec Sec.15's exact numbers: flat +42.857%, hybrid guaranteed-fee
    change 0%, no-renew guaranteed spend $0, measurement_alignment weak for
    flat / strong for hybrid, measurement_exposure high for flat."""
    scenarios = scenario_rules.build_scenarios(latest_fee=4200.0, current_ask=6000.0)
    by_id = {s["id"]: s for s in scenarios}
    flat_assessment = scenario_rules.assess_scenario(by_id["flat"], latest_fee=4200.0, has_caution=True, growth_objective_value="new_customer_acquisition")
    hybrid_assessment = scenario_rules.assess_scenario(by_id["hybrid"], latest_fee=4200.0, has_caution=True, growth_objective_value="new_customer_acquisition")
    no_renew_assessment = scenario_rules.assess_scenario(by_id["do_not_renew"], latest_fee=4200.0, has_caution=True, growth_objective_value="new_customer_acquisition")

    assert flat_assessment["change_vs_latest_fee_pct"] == pytest.approx(42.857, abs=0.01)
    assert flat_assessment["measurement_alignment"] == "weak"
    assert flat_assessment["measurement_exposure"] == "high"
    assert flat_assessment["strategy_alignment"] == "moderate"

    assert hybrid_assessment["change_vs_latest_fee_pct"] == 0.0
    assert hybrid_assessment["measurement_alignment"] == "strong"
    assert hybrid_assessment["measurement_exposure"] == "low"
    assert hybrid_assessment["strategy_alignment"] == "strong"

    assert no_renew_assessment["guaranteed_spend"] == 0.0
    assert no_renew_assessment["relationship_continuity"] == "low"
    assert no_renew_assessment["measurement_alignment"] == "unknown"


def test_no_caution_yields_strong_measurement_alignment_and_low_exposure():
    scenarios = scenario_rules.build_scenarios(latest_fee=5500.0, current_ask=8000.0)
    by_id = {s["id"]: s for s in scenarios}
    flat_assessment = scenario_rules.assess_scenario(by_id["flat"], latest_fee=5500.0, has_caution=False, growth_objective_value="new_customer_acquisition")
    assert flat_assessment["measurement_alignment"] == "strong"
    assert flat_assessment["measurement_exposure"] == "low"
    assert flat_assessment["change_vs_latest_fee_pct"] == pytest.approx(45.4545, abs=0.01)


def test_unknown_growth_objective_yields_unknown_strategy_alignment():
    scenarios = scenario_rules.build_scenarios(latest_fee=3200.0, current_ask=3500.0)
    by_id = {s["id"]: s for s in scenarios}
    for scenario in by_id.values():
        assessment = scenario_rules.assess_scenario(scenario, latest_fee=3200.0, has_caution=False, growth_objective_value=None)
        assert assessment["strategy_alignment"] == "unknown"


def test_relationship_continuity_rule():
    scenarios = scenario_rules.build_scenarios(latest_fee=3600.0, current_ask=3800.0)
    for s in scenarios:
        assessment = scenario_rules.assess_scenario(s, latest_fee=3600.0, has_caution=False, growth_objective_value=None)
        expected = "low" if s["id"] == "do_not_renew" else "high"
        assert assessment["relationship_continuity"] == expected


def test_no_fake_overall_score_field():
    scenarios = scenario_rules.build_scenarios(latest_fee=4200.0, current_ask=6000.0)
    assessment = scenario_rules.assess_scenario(scenarios[0], latest_fee=4200.0, has_caution=True, growth_objective_value="new_customer_acquisition")
    assert "score" not in assessment
    assert "overall" not in assessment


# ---- ScenarioComparisonEvidence assembly (Summit Sisters) ----

def test_summit_sisters_evidence_has_all_three_campaigns_and_exact_roas(db):
    ctx = build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)
    ev = ctx["evidence"]
    assert len(ev.campaigns) == 3
    may = next(c for c in ev.campaigns if c.campaign_id == "camp_summit_2026_05")
    assert may.attributed_roas == 7.44
    assert may.link_clicks == 385
    assert may.code_redemptions == 1847
    assert len(ev.measurement_cautions) == 1
    assert ev.measurement_cautions[0].claim_class == "hypothesis"
    assert ev.measurement_cautions[0].status == "needs_review"


def test_summit_sisters_evidence_client_context_scoped_to_planning_predicates(db):
    # Fresh seed only has partnership_strategy on file - primary_growth_objective
    # and accepts_tradeoff are created by the scripted Step-2 chat flow, not
    # seeded. This test verifies scope (never anything outside the three
    # allowed predicates), not that all three happen to exist yet.
    ctx = build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)
    predicates = {c.predicate for c in ctx["evidence"].client_context}
    assert predicates == {"partnership_strategy"}
    assert predicates <= {"partnership_strategy", "primary_growth_objective", "accepts_tradeoff"}


def test_summit_sisters_scenarios_match_worked_numbers(db):
    ctx = build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)
    by_id = {s.scenario.id: s for s in ctx["evidence"].scenarios}
    assert by_id["flat"].assessment.change_vs_latest_fee_pct == pytest.approx(42.857, abs=0.01)
    assert by_id["hybrid"].assessment.change_vs_latest_fee_pct == 0.0
    assert by_id["do_not_renew"].assessment.guaranteed_spend == 0.0


def test_unknown_partner_returns_none(db):
    assert build_scenario_comparison_context(db, partner_id="does_not_exist", client_id="northwind", current_ask=1000.0) is None


# ---- archetype differentiation (Peak Pursuit / Campfire Kate / Backcountry Ben) ----

def test_peak_pursuit_strong_clean_high_ask(db):
    ctx = build_scenario_comparison_context(db, partner_id="peak_pursuit", client_id="northwind", current_ask=8000.0)
    ev = ctx["evidence"]
    assert ev.measurement_cautions == []
    assert ev.performance_stats.average_roas >= 3.0
    flat = next(s for s in ev.scenarios if s.scenario.id == "flat")
    assert flat.assessment.change_vs_latest_fee_pct == pytest.approx(45.4545, abs=0.01)
    # No caution -> clean measurement alignment/exposure even for a large increase.
    assert flat.assessment.measurement_alignment == "strong"
    assert flat.assessment.measurement_exposure == "low"


def test_campfire_kate_moderate_clean_strategic_fit_not_governed(db):
    ctx = build_scenario_comparison_context(db, partner_id="campfire_kate", client_id="northwind", current_ask=3500.0)
    ev = ctx["evidence"]
    assert ev.measurement_cautions == []
    assert 1.5 <= ev.performance_stats.average_roas < 3.0
    assert ev.partner.partner_note is not None and "first-time buyers" in ev.partner.partner_note
    assert ev.partner_memory == []  # audience-fit note is structured source data, not governed memory


def test_backcountry_ben_weak_roas_high_engagement_clean_measurement(db):
    ctx = build_scenario_comparison_context(db, partner_id="backcountry_ben", client_id="northwind", current_ask=3800.0)
    ev = ctx["evidence"]
    assert ev.measurement_cautions == []
    assert ev.performance_stats.average_roas < 1.5
    assert ev.performance_stats.average_engagement_rate > 0.08


def test_the_four_partners_produce_different_evidence(db):
    """spec Sec.19: the comparisons must feel materially different because
    the underlying evidence differs, not because of cosmetic variation."""
    summit = build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)["evidence"]
    peak = build_scenario_comparison_context(db, partner_id="peak_pursuit", client_id="northwind", current_ask=8000.0)["evidence"]
    kate = build_scenario_comparison_context(db, partner_id="campfire_kate", client_id="northwind", current_ask=3500.0)["evidence"]
    ben = build_scenario_comparison_context(db, partner_id="backcountry_ben", client_id="northwind", current_ask=3800.0)["evidence"]

    caution_flags = {len(e.measurement_cautions) > 0 for e in (summit, peak, kate, ben)}
    assert caution_flags == {True, False}  # Summit has one, the synthetic three don't

    roas_tiers = [e.performance_stats.average_roas for e in (summit, peak, kate, ben)]
    assert len(set(round(r, 1) for r in roas_tiers)) == 4  # four genuinely distinct performance levels


# ---- current-state isolation from Historical Retrieval (spec Sec.22) ----

def test_scenario_comparison_uses_only_latest_active_strategy_after_chain(db):
    _supersede_strategy(db, "reduce_coupon_dependence")
    _supersede_strategy(db, "prioritize_high_intent_creator_partnerships")

    ctx = build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)
    values = {c.value for c in ctx["evidence"].client_context}
    assert values & {"aggressively_grow_coupon_partnerships", "reduce_coupon_dependence"} == set()
    assert "prioritize_high_intent_creator_partnerships" in values

    # Historical Retrieval must still return the full 3-version chain -
    # Scenario Comparison must not have blurred the two retrieval modes.
    history = run_memory_history(db, subject_type="client", subject_id="northwind", predicate="partnership_strategy")
    assert len(history.timeline.changes) == 3


# ---- run_scenario_comparison / mock LLM layer ----

def test_run_scenario_comparison_preferred_id_is_always_valid(db):
    result = run_scenario_comparison(db, client_id="northwind", partner_id="summit_sisters", current_ask=6000.0)
    assert result is not None
    valid_ids = {s.scenario.id for s in result.evidence.scenarios}
    assert result.preferred_scenario_id in valid_ids


def test_run_scenario_comparison_unknown_partner_returns_none(db):
    assert run_scenario_comparison(db, client_id="northwind", partner_id="does_not_exist", current_ask=1000.0) is None


def test_mock_never_invents_a_fourth_scenario(db):
    result = run_scenario_comparison(db, client_id="northwind", partner_id="peak_pursuit", current_ask=8000.0)
    assert len(result.evidence.scenarios) == 3


# ---- malformed / invented-scenario-id fallback (spec Sec.9, Sec.23) ----

class _BrokenScenarioProvider(LLMProvider):
    name = "broken_scenario_test_provider"

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

    def summarize_history(self, *a, **k):
        raise NotImplementedError

    def compare_scenarios(self, evidence):
        return {
            "preferred_scenario_id": "premium_upgrade",  # not one of the supplied ids
            "comparison_summary": "ok",
            "confidence": 0.5,
        }

    def propose_plan(self, *a, **k):
        raise NotImplementedError


def test_invented_scenario_id_falls_back_to_mock(monkeypatch, db):
    monkeypatch.setattr(factory, "get_provider", lambda: _BrokenScenarioProvider())
    ctx = build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)
    valid_ids = {s.scenario.id for s in ctx["evidence"].scenarios}
    result, provider_name = generate_scenario_comparison(ctx["evidence"].model_dump(), valid_scenario_ids=valid_ids)
    assert provider_name.endswith("(fallback)")
    assert result["preferred_scenario_id"] in valid_ids


class _MissingFieldScenarioProvider(_BrokenScenarioProvider):
    def compare_scenarios(self, evidence):
        return {"comparison_summary": "ok", "confidence": 0.5}  # missing preferred_scenario_id


class _BadConfidenceScenarioProvider(_BrokenScenarioProvider):
    def compare_scenarios(self, evidence):
        return {"preferred_scenario_id": "flat", "comparison_summary": "ok", "confidence": 1.5}


class _MalformedArrayScenarioProvider(_BrokenScenarioProvider):
    def compare_scenarios(self, evidence):
        return {"preferred_scenario_id": "flat", "comparison_summary": "ok", "confidence": 0.5, "tradeoffs": "not a list"}


class _RaisesScenarioProvider(_BrokenScenarioProvider):
    def compare_scenarios(self, evidence):
        raise ValueError("simulated provider failure")


@pytest.mark.parametrize("provider_cls", [
    _MissingFieldScenarioProvider, _BadConfidenceScenarioProvider, _MalformedArrayScenarioProvider, _RaisesScenarioProvider,
])
def test_every_malformed_mode_falls_back_safely(monkeypatch, db, provider_cls):
    monkeypatch.setattr(factory, "get_provider", lambda: provider_cls())
    ctx = build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)
    valid_ids = {s.scenario.id for s in ctx["evidence"].scenarios}
    result, provider_name = generate_scenario_comparison(ctx["evidence"].model_dump(), valid_scenario_ids=valid_ids)
    assert provider_name.endswith("(fallback)")
    assert result["preferred_scenario_id"] in valid_ids
    assert 0.0 <= result["confidence"] <= 1.0


# ---- read-only guarantee (spec Sec.20, Sec.24) ----

def test_scenario_comparison_produces_no_mutations(db):
    claims_before = db.query(MemoryClaim).count()
    candidates_before = db.query(MemoryCandidate).count()
    decisions_before = db.query(Decision).count()
    outcomes_before = db.query(Outcome).count()
    pattern_before = db.get(PortfolioPattern, "pattern_hybrid_comp").evidence_count

    build_scenario_comparison_context(db, partner_id="summit_sisters", client_id="northwind", current_ask=6000.0)
    run_scenario_comparison(db, client_id="northwind", partner_id="summit_sisters", current_ask=6000.0)
    run_scenario_comparison(db, client_id="northwind", partner_id="peak_pursuit", current_ask=8000.0)

    assert db.query(MemoryClaim).count() == claims_before
    assert db.query(MemoryCandidate).count() == candidates_before
    assert db.query(Decision).count() == decisions_before
    assert db.query(Outcome).count() == outcomes_before
    assert db.get(PortfolioPattern, "pattern_hybrid_comp").evidence_count == pattern_before
