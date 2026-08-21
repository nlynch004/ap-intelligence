from typing import NamedTuple


class PredicateSpec(NamedTuple):
    subject_types: tuple[str, ...]
    description: str


CANONICAL_PREDICATES: dict[str, PredicateSpec] = {
    "partnership_strategy": PredicateSpec(("client",), "overall partnership/channel-mix strategy direction"),
    "primary_growth_objective": PredicateSpec(("client",), "client's primary growth objective"),
    "accepts_tradeoff": PredicateSpec(("client",), "a tradeoff the client has explicitly accepted"),
    "relationship_status": PredicateSpec(("creator", "publisher"), "current status of AP's relationship with a partner"),
    "negotiation_history": PredicateSpec(("creator", "publisher"), "history of negotiations with a partner"),
    "attribution_integrity_risk": PredicateSpec(("campaign",), "a suspected attribution/measurement risk on a campaign"),
    "partner_performance_pattern": PredicateSpec(
        ("creator", "publisher"),
        "a partner's demonstrated commercial/content performance pattern, characterized from campaign-review "
        "evidence - historical observation, not a causal claim or a guarantee of future results",
    ),
}

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
    key = raw_predicate.strip().lower()
    if key in CANONICAL_PREDICATES:
        return key, True
    if key in PREDICATE_ALIASES:
        return PREDICATE_ALIASES[key], True
    return raw_predicate, False
