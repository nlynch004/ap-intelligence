"""Canonical predicate vocabulary + deterministic alias normalization.

Conflict detection in `conflict_resolver.py` is an exact-string match on
(subject_type, subject_id, predicate) by design (spec Sec.11) - it does not
do semantic matching. That means the extraction agent's choice of predicate
string is load-bearing: if it names a concept differently than an existing
claim, conflict detection silently misses it. This is not hypothetical - a
live OpenAI call during the pre-launch audit split the Northwind
strategy-update message differently than expected and initially omitted a
`partnership_strategy` claim entirely, which would have skipped the
SUPERSEDE step of the demo.

This module is the single deterministic seam that catches predicate drift
before it reaches `conflict_resolver`. It is intentionally NOT a fuzzy /
semantic matcher - it is a small, explicit, human-curated lookup table, in
keeping with the codebase's principle that deterministic code owns conflict
lookup (spec Sec.22) and the model only proposes.
"""

from typing import NamedTuple


class PredicateSpec(NamedTuple):
    subject_types: tuple[str, ...]
    description: str


# The canonical, application-recognized predicate vocabulary. Anything not
# in this set after alias normalization is treated as UNKNOWN (see
# `normalize_predicate`) rather than silently created or silently coerced
# into one of these buckets.
CANONICAL_PREDICATES: dict[str, PredicateSpec] = {
    "partnership_strategy": PredicateSpec(("client",), "overall partnership/channel-mix strategy direction"),
    "primary_growth_objective": PredicateSpec(("client",), "client's primary growth objective"),
    "accepts_tradeoff": PredicateSpec(("client",), "a tradeoff the client has explicitly accepted"),
    "relationship_status": PredicateSpec(("creator", "publisher"), "current status of AP's relationship with a partner"),
    "negotiation_history": PredicateSpec(("creator", "publisher"), "history of negotiations with a partner"),
    "attribution_integrity_risk": PredicateSpec(("campaign",), "a suspected attribution/measurement risk on a campaign"),
    # Phase 2 (Campaign Review) addition - the single new predicate that
    # phase required. Justification: campaign-review lessons that
    # characterize a partner's demonstrated commercial/content performance
    # (e.g. "consistently strong direct-response economics", "weak
    # direct-response economics despite content strength") don't fit any
    # existing predicate - relationship_status describes relationship stage,
    # not performance, and negotiation_history describes negotiation
    # events, not outcomes. attribution_integrity_risk was deliberately
    # reused as-is for campaign-level measurement concerns rather than
    # duplicated. Anything that doesn't fit even this (e.g. audience-fit
    # characterizations like "indexes toward first-time buyers") is left
    # unknown on purpose and routed to REQUEST_HUMAN_REVIEW - not every
    # useful observation needs a new canonical bucket.
    "partner_performance_pattern": PredicateSpec(
        ("creator", "publisher"),
        "a partner's demonstrated commercial/content performance pattern, characterized from campaign-review "
        "evidence - historical observation, not a causal claim or a guarantee of future results",
    ),
}

# Deterministic, explicit alias table. Every key is a plausible synonym the
# extraction agent (LLM or mock) might emit for a canonical predicate above.
# This is a fixed lookup, not inferred at runtime - extending it is a
# reviewed code change, matching "deterministic code owns conflict lookup."
PREDICATE_ALIASES: dict[str, str] = {
    "client_strategy": "partnership_strategy",
    "channel_strategy": "partnership_strategy",
    "coupon_strategy": "partnership_strategy",
    "growth_strategy": "partnership_strategy",
    "partnership_direction": "partnership_strategy",
    "strategy": "partnership_strategy",
    "primary_goal": "primary_growth_objective",
    "growth_objective": "primary_growth_objective",
    "main_objective": "primary_growth_objective",
    "customer_acquisition_goal": "primary_growth_objective",
    "growth_goal": "primary_growth_objective",
    "tradeoff": "accepts_tradeoff",
    "accepted_tradeoff": "accepts_tradeoff",
    "roas_tradeoff": "accepts_tradeoff",
    "partner_status": "relationship_status",
    "relationship": "relationship_status",
    "attribution_risk": "attribution_integrity_risk",
    "promo_code_leakage_risk": "attribution_integrity_risk",
    "performance_pattern": "partner_performance_pattern",
    "performance_characterization": "partner_performance_pattern",
    "commerce_performance_pattern": "partner_performance_pattern",
    "commercial_performance_pattern": "partner_performance_pattern",
}


def normalize_predicate(raw_predicate: str) -> tuple[str, bool]:
    """Normalize a raw predicate string against the canonical vocabulary.

    Returns (normalized_predicate, is_known):
    - If `raw_predicate` (case/whitespace-insensitive) is already canonical,
      or is a known alias, returns the canonical name and True.
    - Otherwise returns `raw_predicate` UNCHANGED and False - genuinely
      unknown concepts are never coerced into an existing bucket.
    """
    key = raw_predicate.strip().lower()
    if key in CANONICAL_PREDICATES:
        return key, True
    if key in PREDICATE_ALIASES:
        return PREDICATE_ALIASES[key], True
    return raw_predicate, False
