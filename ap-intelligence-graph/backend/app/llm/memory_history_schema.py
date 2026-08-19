"""Pydantic validation for raw historical-synthesis-agent output (spec
Phase 4). Same role as the other llm/*_schema.py modules: validates the
shape `llm/factory.py::call_with_fallback` checks before trusting a live
response; a structurally invalid result falls back to the deterministic
mock provider exactly like a call failure would.

The structured MemoryHistoryTimeline (app/memory/retrieval.py) is the
source of truth; this is only the narrative layer over it, and it is
allowed to be entirely empty (no forced narrative when there's nothing to
narrate - see RawHistoricalSummaryOut's all-optional fields)."""

from pydantic import BaseModel, ConfigDict


class RawHistoricalSummaryOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str = ""
    material_changes: list[str] = []
    current_state: str = ""
    historical_context: list[str] = []


def validate_raw_historical_summary(raw: object) -> dict:
    """Raises on any structural problem; returns a plain dict on success."""
    return RawHistoricalSummaryOut(**raw).model_dump()
