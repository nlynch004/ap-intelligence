from typing import Any

from app.llm.factory import call_with_fallback
from app.llm.scenario_comparison_schema import validate_raw_scenario_comparison


def generate_scenario_comparison(evidence: dict[str, Any], *, valid_scenario_ids: set[str]) -> tuple[dict, str]:

    def _validate(raw: object) -> dict:
        result = validate_raw_scenario_comparison(raw)
        if result["preferred_scenario_id"] not in valid_scenario_ids:
            raise ValueError(f"preferred_scenario_id {result['preferred_scenario_id']!r} is not one of the supplied scenario ids")
        return result

    result, provider_name = call_with_fallback("compare_scenarios", evidence, validate=_validate)
    return result, provider_name
