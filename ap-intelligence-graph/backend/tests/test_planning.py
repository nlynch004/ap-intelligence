"""Tests for Phase 6: Account Planning (Plan / PlannedAction persistence).

Covers deterministic PlanningContext assembly (app.memory.retrieval::
build_planning_context, current-state-only strategy), id sanitization
(app.memory.planning_rules), the read-only proposal step vs. the persisting
create_plan step, the duplicate-action guard (both within one request and
against already-persisted open actions), owner/status/due-date editing,
malformed/invented-id LLM fallback behavior, reset removing Plans/
PlannedActions, and persistence surviving a fresh DB session.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config_module
import app.seed as seed_module
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import schemas
from app.agents.plan_agent import generate_plan_proposal
from app.llm.provider import LLMProvider
from app.memory import planning_rules
from app.memory.manager import create_plan, list_plans_for_client, propose_plan, update_plan, update_planned_action
from app.memory.operations import execute_supersede
from app.memory.retrieval import build_planning_context
from app.models import Decision, MemoryClaim, Plan, PlannedAction


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_planning.db"
    engine = create_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(seed_module, "engine", engine)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)  # force deterministic mock

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    seed_module.seed(session, reset=True)
    yield session
    session.close()


def _row_counts(db):
    return db.query(Plan).count(), db.query(PlannedAction).count()


# ---- PlanningContext ----


def test_planning_context_scoped_to_active_strategy_only(db):
    ctx = build_planning_context(db, client_id="northwind")
    predicates = {c.predicate for c in ctx.client.current_strategy}
    assert predicates <= {"partnership_strategy", "primary_growth_objective", "accepts_tradeoff"}
    assert all(c.claim_id for c in ctx.client.current_strategy)


def test_planning_context_excludes_superseded_strategy(db):
    existing = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.subject_type == "client", MemoryClaim.subject_id == "northwind",
                MemoryClaim.predicate == "partnership_strategy", MemoryClaim.status == "active")
        .one()
    )
    payload = {
        "type": "client_preference", "subject_type": "client", "subject_id": "northwind",
        "subject_label": "Northwind Outfitters", "predicate": "partnership_strategy",
        "value": "reduce_coupon_dependence", "claim_class": "verified_fact", "confidence": 0.95,
    }
    execute_supersede(db, existing, payload, client_id="northwind", source={"type": "account_team_statement"})
    db.commit()

    ctx = build_planning_context(db, client_id="northwind")
    values = {c.value for c in ctx.client.current_strategy if c.predicate == "partnership_strategy"}
    assert values == {"reduce_coupon_dependence"}
    assert "aggressively_grow_coupon_partnerships" not in values


def test_planning_context_defaults_to_partners_with_campaign_history(db):
    ctx = build_planning_context(db, client_id="northwind")
    partner_ids = {p.partner.partner_id for p in ctx.partners}
    assert "summit_sisters" in partner_ids
    assert "peak_pursuit" in partner_ids
    # Every partner in scope actually has campaign history - the context
    # builder's default scope is never "every partner in the system."
    assert all(p.performance_stats.campaign_count > 0 for p in ctx.partners)


def test_planning_context_scenario_input_attaches_to_matching_partner_only(db):
    ctx = build_planning_context(db, client_id="northwind")
    ss = next(p for p in ctx.partners if p.partner.partner_id == "summit_sisters")
    scenario = schemas.ScenarioComparisonRef(
        partner_id="summit_sisters", preferred_scenario_id="hybrid", comparison_summary="test",
        scenarios=[schemas.ScenarioWithAssessment(
            scenario=schemas.RenewalScenario(id="hybrid", type="hybrid", label="Hybrid", base_fee=4200, performance_bonus_pct=15, bonus_basis="verified_new_customer_revenue", renews_relationship=True),
            assessment=schemas.ScenarioAssessment(scenario_id="hybrid", guaranteed_spend=4200, change_vs_latest_fee_pct=0.0, compensation_structure="Performance-linked", strategy_alignment="strong", measurement_alignment="strong", measurement_exposure="low", relationship_continuity="high"),
        )],
    )
    ctx2 = build_planning_context(db, client_id="northwind", scenario_inputs=[scenario])
    ss2 = next(p for p in ctx2.partners if p.partner.partner_id == "summit_sisters")
    other = next(p for p in ctx2.partners if p.partner.partner_id != "summit_sisters")
    assert ss2.scenario is not None and ss2.scenario.preferred_scenario_id == "hybrid"
    assert other.scenario is None
    assert ss.scenario is None  # unaffected context (no scenario_inputs) has none


# ---- id sanitization (app.memory.planning_rules) ----


def test_sanitize_drops_action_naming_unknown_partner(db):
    ctx = build_planning_context(db, client_id="northwind")
    raw = {"partner_id": "not_a_real_partner", "action_type": "renew", "summary": "s", "rationale": "r"}
    assert planning_rules.sanitize_proposed_action(raw, context=ctx, index=0) is None


def test_sanitize_filters_invented_memory_and_campaign_ids(db):
    ctx = build_planning_context(db, client_id="northwind")
    partner_id = ctx.partners[0].partner.partner_id
    real_memory_id = ctx.client.current_strategy[0].claim_id
    raw = {
        "partner_id": partner_id, "action_type": "follow_up", "summary": "s", "rationale": "r",
        "supporting_memory_ids": [real_memory_id, "invented_claim_id"],
        "supporting_campaign_ids": ["invented_campaign_id"],
    }
    sanitized = planning_rules.sanitize_proposed_action(raw, context=ctx, index=0)
    assert sanitized.supporting_memory_ids == [real_memory_id]
    assert sanitized.supporting_campaign_ids == []


def test_sanitize_drops_scenario_id_not_present_for_that_partner(db):
    ctx = build_planning_context(db, client_id="northwind")
    partner_id = ctx.partners[0].partner.partner_id
    raw = {"partner_id": partner_id, "action_type": "renegotiate", "summary": "s", "rationale": "r", "source_scenario_id": "hybrid"}
    sanitized = planning_rules.sanitize_proposed_action(raw, context=ctx, index=0)
    assert sanitized.source_scenario_id is None  # no scenario was ever supplied for this partner


def test_sanitize_flags_duplicate_open_action(db):
    ctx = build_planning_context(db, client_id="northwind")
    partner_id = ctx.partners[0].partner.partner_id
    ctx_with_open = ctx.model_copy(update={
        "existing_open_actions": [schemas.PlanningExistingActionRef(id="existing_1", partner_id=partner_id, action_type="renew", summary="already open", status="approved")],
    })
    raw = {"partner_id": partner_id, "action_type": "renew", "summary": "s", "rationale": "r"}
    sanitized = planning_rules.sanitize_proposed_action(raw, context=ctx_with_open, index=0)
    assert sanitized.duplicate_of_planned_action_id == "existing_1"


# ---- propose_plan: read-only, differentiated, no fake ids ----


def test_propose_plan_creates_zero_rows(db):
    before = _row_counts(db)
    proposal = propose_plan(db, client_id="northwind")
    after = _row_counts(db)
    assert proposal is not None
    assert before == after == (0, 0)


def test_propose_plan_differs_across_partners(db):
    proposal = propose_plan(db, client_id="northwind")
    action_types = {a.action_type for a in proposal.proposed_actions}
    # Summit Sisters carries a real attribution caution the synthetic
    # archetypes don't - the mock must not produce one blanket action type.
    assert len(action_types) >= 2


def test_propose_plan_every_supporting_id_is_real(db):
    proposal = propose_plan(db, client_id="northwind")
    valid_memory = planning_rules.valid_memory_ids(proposal.context)
    valid_campaigns = planning_rules.valid_campaign_ids(proposal.context)
    for a in proposal.proposed_actions:
        assert set(a.supporting_memory_ids) <= valid_memory
        assert set(a.supporting_campaign_ids) <= valid_campaigns
        assert a.partner_id in planning_rules.valid_partner_ids(proposal.context)


def test_propose_plan_unknown_client_returns_none(db):
    assert propose_plan(db, client_id="does_not_exist") is None


# ---- generate_plan_proposal: validation/fallback ----


class _BrokenPlanProviderBase(LLMProvider):
    name = "broken_plan_test_provider"

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

    def compare_scenarios(self, *a, **k):
        raise NotImplementedError


class _AllInventedPartnerProvider(_BrokenPlanProviderBase):
    def propose_plan(self, context):
        return {
            "plan_name": "Bogus Plan", "objective": "Bogus objective",
            "proposed_actions": [{"partner_id": "totally_invented_partner", "action_type": "renew", "summary": "s", "rationale": "r"}],
        }


class _MissingFieldPlanProvider(_BrokenPlanProviderBase):
    def propose_plan(self, context):
        return {"objective": "no plan_name here"}


class _RaisesPlanProvider(_BrokenPlanProviderBase):
    def propose_plan(self, context):
        raise RuntimeError("simulated provider outage")


@pytest.mark.parametrize("provider_cls", [_AllInventedPartnerProvider, _MissingFieldPlanProvider, _RaisesPlanProvider])
def test_broken_provider_falls_back_to_mock(monkeypatch, db, provider_cls):
    import app.llm.factory as factory

    monkeypatch.setattr(factory, "get_provider", lambda: provider_cls())
    ctx = build_planning_context(db, client_id="northwind")
    result, provider_name = generate_plan_proposal(ctx)
    assert "fallback" in provider_name
    assert result["plan_name"]
    for a in result["proposed_actions"]:
        assert a["partner_id"] in planning_rules.valid_partner_ids(ctx)


# ---- create_plan: persistence, duplicate guard, rejection semantics ----


def test_create_plan_persists_plan_and_approved_actions(db):
    req = schemas.PlanCreateRequest(
        client_id="northwind", name="Northwind Test Plan", objective="Test objective",
        actions=[
            schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="renegotiate", summary="Renegotiate Summit Sisters", rationale="r"),
            schemas.PlannedActionCreate(partner_id="peak_pursuit", action_type="renew", summary="Renew Peak Pursuit", rationale="r"),
        ],
    )
    result = create_plan(db, req)
    assert result is not None
    assert result.plan.status == "approved"
    assert len(result.plan.actions) == 2
    assert all(a.status == "approved" for a in result.plan.actions)
    assert _row_counts(db) == (1, 2)


def test_create_plan_only_persists_the_actions_passed_in(db):
    """Simulates a human rejecting some proposed actions in the UI - the
    backend never sees the rejected ones at all, so only the approved
    subset the frontend sends ever reaches the database (spec Sec.37)."""
    proposal = propose_plan(db, client_id="northwind")
    assert len(proposal.proposed_actions) >= 2
    approved_only = proposal.proposed_actions[:1]

    req = schemas.PlanCreateRequest(
        client_id="northwind", name=proposal.plan_name, objective=proposal.objective,
        actions=[schemas.PlannedActionCreate(
            partner_id=a.partner_id, action_type=a.action_type, summary=a.summary, rationale=a.rationale,
            supporting_memory_ids=a.supporting_memory_ids, supporting_campaign_ids=a.supporting_campaign_ids,
            source_scenario_id=a.source_scenario_id,
        ) for a in approved_only],
    )
    result = create_plan(db, req)
    assert len(result.plan.actions) == 1
    assert db.query(PlannedAction).count() == 1


def test_create_plan_duplicate_within_same_request_skipped(db):
    req = schemas.PlanCreateRequest(
        client_id="northwind", name="Dup test", objective="o",
        actions=[
            schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="renegotiate", summary="first", rationale="r"),
            schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="renegotiate", summary="duplicate", rationale="r"),
        ],
    )
    result = create_plan(db, req)
    assert len(result.plan.actions) == 1
    assert result.skipped_duplicate_actions == ["duplicate"]


def test_create_plan_duplicate_against_existing_open_action_skipped(db):
    first = schemas.PlanCreateRequest(
        client_id="northwind", name="Plan A", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="renegotiate", summary="original", rationale="r")],
    )
    create_plan(db, first)

    second = schemas.PlanCreateRequest(
        client_id="northwind", name="Plan B", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="renegotiate", summary="second attempt", rationale="r")],
    )
    result = create_plan(db, second)
    assert len(result.plan.actions) == 0
    assert result.skipped_duplicate_actions == ["second attempt"]
    # The second Plan row still gets created (empty) - only the ACTION was
    # a duplicate, not the plan itself.
    assert db.query(Plan).count() == 2
    assert db.query(PlannedAction).count() == 1


def test_create_plan_unknown_client_returns_none(db):
    req = schemas.PlanCreateRequest(client_id="does_not_exist", name="x", objective="o", actions=[])
    assert create_plan(db, req) is None


def test_create_plan_invalid_owner_dropped_not_persisted(db):
    req = schemas.PlanCreateRequest(
        client_id="northwind", name="Owner test", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="follow_up", summary="s", rationale="r", owner_id="not_a_real_team_member")],
    )
    result = create_plan(db, req)
    assert result.plan.actions[0].owner_id is None


# ---- update endpoints ----


def test_update_planned_action_status_owner_due_date(db):
    req = schemas.PlanCreateRequest(
        client_id="northwind", name="Update test", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="follow_up", summary="s", rationale="r")],
    )
    result = create_plan(db, req)
    action_id = result.plan.actions[0].id

    updated = update_planned_action(db, action_id, schemas.PlannedActionUpdate(status="in_progress", owner_id="jessica_moreno", due_date="2026-12-01"))
    assert updated.status == "in_progress"
    assert updated.owner_id == "jessica_moreno"
    assert updated.owner_name == "Jessica Moreno"
    assert updated.due_date == "2026-12-01"


def test_update_planned_action_invalid_owner_rejected(db):
    req = schemas.PlanCreateRequest(
        client_id="northwind", name="Update test 2", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="follow_up", summary="s", rationale="r")],
    )
    result = create_plan(db, req)
    action_id = result.plan.actions[0].id

    updated = update_planned_action(db, action_id, schemas.PlannedActionUpdate(owner_id="invented_person"))
    assert updated.owner_id is None


def test_update_planned_action_missing_returns_none(db):
    assert update_planned_action(db, "not_a_real_action", schemas.PlannedActionUpdate(status="completed")) is None


def test_update_plan_status(db):
    req = schemas.PlanCreateRequest(client_id="northwind", name="Status test", objective="o", actions=[])
    result = create_plan(db, req)
    updated = update_plan(db, result.plan.id, schemas.PlanUpdate(status="active"))
    assert updated.status == "active"


def test_list_plans_for_client(db):
    create_plan(db, schemas.PlanCreateRequest(client_id="northwind", name="Plan 1", objective="o", actions=[]))
    create_plan(db, schemas.PlanCreateRequest(client_id="northwind", name="Plan 2", objective="o", actions=[]))
    plans = list_plans_for_client(db, "northwind")
    assert {p.name for p in plans} == {"Plan 1", "Plan 2"}


# ---- reset + persistence across a fresh session ----


def test_reset_removes_plans_and_planned_actions(db, tmp_path, monkeypatch):
    create_plan(db, schemas.PlanCreateRequest(
        client_id="northwind", name="Will be reset", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="follow_up", summary="s", rationale="r")],
    ))
    assert _row_counts(db) == (1, 1)

    seed_module.seed(db, reset=True)
    assert _row_counts(db) == (0, 0)


def test_plan_persists_across_a_new_db_session(db):
    result = create_plan(db, schemas.PlanCreateRequest(
        client_id="northwind", name="Durable plan", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="follow_up", summary="s", rationale="r")],
    ))
    plan_id = result.plan.id

    NewSession = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    fresh = NewSession()
    try:
        reloaded = fresh.get(Plan, plan_id)
        assert reloaded is not None
        assert reloaded.name == "Durable plan"
        actions = fresh.query(PlannedAction).filter(PlannedAction.plan_id == plan_id).all()
        assert len(actions) == 1
    finally:
        fresh.close()


# ---- Decision -> PlannedAction optional link (spec Sec.26) ----


def test_decision_source_planned_action_id_is_optional_and_additive(db):
    from app.routers.decisions import create_decision

    result = create_plan(db, schemas.PlanCreateRequest(
        client_id="northwind", name="Link test", objective="o",
        actions=[schemas.PlannedActionCreate(partner_id="summit_sisters", action_type="renegotiate", summary="s", rationale="r")],
    ))
    action_id = result.plan.actions[0].id

    linked = create_decision(schemas.DecisionCreateRequest(
        client_id="northwind", partner_id="summit_sisters", summary="Renew under hybrid", terms={}, rationale="r",
        source_planned_action_id=action_id,
    ), db=db)
    assert linked.source_planned_action_id == action_id

    unlinked = create_decision(schemas.DecisionCreateRequest(
        client_id="northwind", partner_id="summit_sisters", summary="Renew flat", terms={}, rationale="r",
    ), db=db)
    assert unlinked.source_planned_action_id is None

    bogus = create_decision(schemas.DecisionCreateRequest(
        client_id="northwind", partner_id="summit_sisters", summary="Renew flat 2", terms={}, rationale="r",
        source_planned_action_id="not_a_real_action",
    ), db=db)
    assert bogus.source_planned_action_id is None
