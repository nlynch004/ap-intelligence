HYBRID_DEFAULT_BONUS_PCT = 15.0

LARGE_INCREASE_THRESHOLD_PCT = 25.0


def build_scenarios(*, latest_fee: float | None, current_ask: float) -> list[dict]:
    flat = {
        "id": "flat", "type": "flat_fee", "label": "Accept requested flat fee",
        "base_fee": current_ask, "performance_bonus_pct": 0.0, "bonus_basis": None,
        "renews_relationship": True,
    }
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
    if not latest_fee:
        return None
    return round((guaranteed_spend - latest_fee) / latest_fee * 100, 3)


def _compensation_structure(scenario: dict) -> str:
    return {"flat_fee": "Flat", "hybrid": "Performance-linked", "do_not_renew": "None"}[scenario["type"]]


def _strategy_alignment(scenario: dict, growth_objective_value: str | None) -> str:
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
