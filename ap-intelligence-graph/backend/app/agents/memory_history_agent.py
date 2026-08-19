"""Memory-history narration agent (spec Phase 4). Input: the
deterministically-ordered timeline dict from
app.memory.retrieval.build_memory_history - never raw DB rows. Output:
optional narrative fields (summary/material_changes/current_state/
historical_context). The model explains history; it never determines it -
version chain, statuses, and dates all come from the timeline itself."""

from app.llm.factory import call_with_fallback
from app.llm.memory_history_schema import validate_raw_historical_summary


def generate_historical_summary(evidence: dict) -> tuple[dict, str]:
    """Returns a dict guaranteed to match RawHistoricalSummaryOut's shape -
    a malformed/incomplete live response falls back to the (always-valid)
    mock provider (see llm/factory.py::call_with_fallback)."""
    result, provider_name = call_with_fallback("summarize_history", evidence, validate=validate_raw_historical_summary)
    return result, provider_name
