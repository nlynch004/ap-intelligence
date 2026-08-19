"""Deterministic Scenario Comparison rules (spec Phase 5).

This module owns ALL scenario construction and qualitative assessment
logic - the LLM never invents a scenario and never rates one; it only ever
sees the fully-assessed result of this module (schemas.ScenarioComparisonEvidence,
built in app/memory/retrieval.py::build_scenario_comparison_context). Every
rule here is a plain, documented if/else - no ML, no fitted scoring model.
This is a prototype PLANNING structure, not an optimization/forecasting
model (spec Sec.3), and it deliberately produces no fake numeric overall
score (spec Sec.6) - only the individually-labeled dimensions below.
"""

# Prototype default, not a computed/optimized figure - documented here as
# the single place it's defined (spec Sec.3: "This is a prototype planning
# structure... Make that explicit in code/comments").
HYBRID_DEFAULT_BONUS_PCT = 15.0

# A guaranteed-fee increase at or above this threshold, under an open
# measurement caution, is treated as "high" exposure (spec Sec.7's "large
# unconditional guaranteed-spend increase" example). A specific, documented
# number rather than a vague notion of "large."
LARGE_INCREASE_THRESHOLD_PCT = 25.0


def build_scenarios(*, latest_fee: float | None, current_ask: float) -> list[dict]:
    """The three renewal scenarios, deterministically constructed (spec
    Sec.1, Sec.3) - generic over any creator, never hardcoded to a specific
    partner. `current_ask` must be supplied by the caller (spec Sec.4: "Do
    not invent" a renewal ask) - this function never fabricates one."""
    flat = {
        "id": "flat", "type": "flat_fee", "label": "Accept requested flat fee",
        "base_fee": current_ask, "performance_bonus_pct": 0.0, "bonus_basis": None,
        "renews_relationship": True,
    }
    # Hybrid's base is the most recent campaign fee, NOT the (possibly much
    # higher) current ask - spec Sec.3's documented prototype rule. Falls
    # back to current_ask only when there is no campaign history at all to
    # anchor a "most recent fee" against.
    hybrid_base = latest_fee if latest_fee is not None else current_ask
    hybrid = {
        "id": "hybrid", "type": "hybrid", "label": "Hybrid: base fee + performance bonus",
        "base_fee": hybrid_base, "performance_bonus_pct": HYBRID_DEFAULT_BONUS_PCT,
        "bonus_basis": "verified_new_customer_revenue", "renews_relationship": True,
    }
    do_not_renew = {
        "id": "do_not_renew", "type": "do_not_renew", "label": "Do not renew",
        "base_fee": 0.0, "performance_bonus_pct": 0.0, "bonus_basis": None,
        "renews_relationship": False,
    }
    return [flat, hybrid, do_not_renew]


def _guaranteed_spend(scenario: dict) -> float:
    return scenario["base_fee"] or 0.0


def _change_vs_latest_fee_pct(guaranteed_spend: float, latest_fee: float | None) -> float | None:
    """Application-calculated, never left to the LLM (spec Sec.6). None
    when there is no latest fee to compare against."""
    if not latest_fee:
        return None
    return round((guaranteed_spend - latest_fee) / latest_fee * 100, 3)


def _compensation_structure(scenario: dict) -> str:
    return {"flat_fee": "Flat", "hybrid": "Performance-linked", "do_not_renew": "None"}[scenario["type"]]


def _strategy_alignment(scenario: dict, growth_objective_value: str | None) -> str:
    """spec Sec.7: 'client objective = new_customer_acquisition + scenario
    compensation explicitly rewards verified new-customer performance ->
    strong.' Generalized past the one literal value: any growth-objective
    value naming 'new_customer' paired with a bonus basis that also names
    'new_customer' is a real, checkable match, not a coincidence. A
    renewing scenario that doesn't specifically reward the objective is
    moderate (it doesn't work against it, but doesn't specifically serve it
    either); not renewing removes a growth lever entirely -> weak. With no
    governed growth objective on file at all, alignment can't be judged
    against anything -> unknown for every scenario (spec Sec.8: prefer
    unknown over invented certainty)."""
    if not growth_objective_value:
        return "unknown"
    rewards_new_customer = scenario.get("bonus_basis") == "verified_new_customer_revenue"
    objective_is_new_customer = "new_customer" in growth_objective_value
    if objective_is_new_customer and rewards_new_customer:
        return "strong"
    if scenario["type"] == "do_not_renew":
        return "weak"
    return "moderate"


def _measurement_alignment(scenario: dict, has_caution: bool, change_pct: float | None) -> str:
    """spec Sec.7's two worked examples: an unconditional flat-fee INCREASE
    under an open attribution caution implicitly leans on the disputed
    number to justify paying more -> weak. A hybrid bonus basis that
    explicitly routes compensation through a verified (not disputed) metric
    -> strong, caution notwithstanding. With no caution at all there is
    nothing disputed to misalign with, so any renewing structure is
    strong. Not renewing has no ongoing compensation to (mis)align at
    all -> unknown, not forced into a rating."""
    if scenario["type"] == "do_not_renew":
        return "unknown"
    if not has_caution:
        return "strong"
    if scenario["type"] == "hybrid" and scenario.get("bonus_basis") == "verified_new_customer_revenue":
        return "strong"
    if scenario["type"] == "flat_fee" and change_pct is not None and change_pct > 0:
        return "weak"
    return "moderate"


def _measurement_exposure(scenario: dict, has_caution: bool, change_pct: float | None) -> str:
    """spec Sec.7: 'large unconditional guaranteed-spend increase +
    measurement caution exists -> high.' A hybrid bonus basis tied to a
    verified metric only exposes the flat (unmeasured) guaranteed base, not
    a disputed number -> low. No caution at all -> low regardless of
    scenario size, since nothing disputed exists to be exposed to."""
    if scenario["type"] == "do_not_renew" or not has_caution:
        return "low"
    if scenario["type"] == "hybrid":
        return "low" if scenario.get("bonus_basis") == "verified_new_customer_revenue" else "moderate"
    if scenario["type"] == "flat_fee":
        if change_pct is not None and change_pct >= LARGE_INCREASE_THRESHOLD_PCT:
            return "high"
        return "moderate"
    return "unknown"


def _relationship_continuity(scenario: dict) -> str:
    """spec Sec.7: flat/hybrid renewal -> high; do-not-renew -> low. This
    is only ONE dimension among several - deliberately not weighted or
    combined into an overall score, so it cannot by itself make renewal
    "win" (spec Sec.7: "Do not bias the system so renewal automatically
    wins")."""
    return "low" if scenario["type"] == "do_not_renew" else "high"


def assess_scenario(scenario: dict, *, latest_fee: float | None, has_caution: bool, growth_objective_value: str | None) -> dict:
    guaranteed_spend = _guaranteed_spend(scenario)
    change_pct = _change_vs_latest_fee_pct(guaranteed_spend, latest_fee)
    return {
        "scenario_id": scenario["id"],
        "guaranteed_spend": guaranteed_spend,
        "change_vs_latest_fee_pct": change_pct,
        "compensation_structure": _compensation_structure(scenario),
        "strategy_alignment": _strategy_alignment(scenario, growth_objective_value),
        "measurement_alignment": _measurement_alignment(scenario, has_caution, change_pct),
        "measurement_exposure": _measurement_exposure(scenario, has_caution, change_pct),
        "relationship_continuity": _relationship_continuity(scenario),
    }
