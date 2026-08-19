"""Partner brief agent (spec Phase 3). Input: PartnerBriefEvidence only
(already deterministically assembled - see app/memory/retrieval.py). Output:
structured relationship_summary/performance_summary/what_to_know/
negotiation_considerations/measurement_considerations/open_questions/
planning_implications. Read-only preparation - no candidate lessons, nothing
is proposed for persistence (unlike the campaign review agent)."""

from app.llm.factory import call_with_fallback
from app.llm.partner_brief_schema import validate_raw_partner_brief


def generate_partner_brief(evidence: dict) -> tuple[dict, str]:
    """Returns a dict guaranteed to match RawPartnerBriefOut's shape - the
    raw LLM result is validated before it is trusted; a malformed/incomplete
    live response falls back to the (always-valid) mock provider (see
    llm/factory.py::call_with_fallback)."""
    result, provider_name = call_with_fallback("generate_partner_brief", evidence, validate=validate_raw_partner_brief)
    return result, provider_name
