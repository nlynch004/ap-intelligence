"""Scenario comparison agent (spec Phase 5). Input:
ScenarioComparisonEvidence.model_dump() - three already-constructed,
already-assessed renewal scenarios (app.memory.scenario_rules), never raw
DB rows. Output: which of the supplied scenarios is preferred plus
narrative fields. The model explains and chooses among the options; it
never builds or rates them."""

from typing import Any

from app.llm.factory import call_with_fallback
from app.llm.scenario_comparison_schema import validate_raw_scenario_comparison


def generate_scenario_comparison(evidence: dict[str, Any], *, valid_scenario_ids: set[str]) -> tuple[dict, str]:
    """Returns a dict guaranteed to match RawScenarioComparisonOut's shape
    AND whose preferred_scenario_id is one of `valid_scenario_ids` - an
    invented scenario id is treated exactly like a structurally invalid
    response (spec Sec.9: "Reject/fallback if the model returns an
    invented scenario ID") and falls back to the deterministic mock, which
    can only ever pick from the scenarios it was actually given."""

    def _validate(raw: object) -> dict:
        result = validate_raw_scenario_comparison(raw)
        if result["preferred_scenario_id"] not in valid_scenario_ids:
            raise ValueError(f"preferred_scenario_id {result['preferred_scenario_id']!r} is not one of the supplied scenario ids")
        return result

    result, provider_name = call_with_fallback("compare_scenarios", evidence, validate=_validate)
    return result, provider_name
