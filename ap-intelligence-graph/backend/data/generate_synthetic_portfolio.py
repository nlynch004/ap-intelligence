"""One-time generator for backend/data/synthetic_portfolio.json.

Produces AP's *privacy-safe portfolio layer*: fictional clients, creators,
account-team members, historical creator-renewal decisions, relationship
memories, and portfolio patterns. All of it is synthetic and is labeled as
such wherever it surfaces in the UI (scope.synthetic = true).

Deterministic (fixed random seed) so the fixture is reproducible. Run with:
    uv run python data/generate_synthetic_portfolio.py
"""

import json
import random
from pathlib import Path

random.seed(42)

OUT_PATH = Path(__file__).parent / "synthetic_portfolio.json"

CLIENTS = [
    {"id": "aurora_fitco", "name": "Aurora FitCo", "industry": "activewear", "growth_stage": "scaling"},
    {"id": "coastal_kitchen", "name": "Coastal Kitchen Co.", "industry": "home & kitchen", "growth_stage": "mature"},
    {"id": "pinehollow_supply", "name": "Pinehollow Supply", "industry": "outdoor apparel", "growth_stage": "scaling"},
    {"id": "verdant_skincare", "name": "Verdant Skincare", "industry": "beauty", "growth_stage": "early_growth"},
    {"id": "haulwell_gear", "name": "Haulwell Gear", "industry": "outdoor apparel", "growth_stage": "mature"},
]

CREATORS = [
    {"id": "ridgeline_rae", "name": "Ridgeline Rae", "platform": "Instagram", "category": "outdoor"},
    {"id": "basecamp_bri", "name": "Basecamp Bri", "platform": "YouTube", "category": "outdoor"},
    {"id": "fitwith_farah", "name": "Fit With Farah", "platform": "TikTok", "category": "activewear"},
    {"id": "kettle_and_kin", "name": "Kettle & Kin", "platform": "Instagram", "category": "home & kitchen"},
    {"id": "glowlab_gigi", "name": "Glowlab Gigi", "platform": "TikTok", "category": "beauty"},
    {"id": "trailmix_theo", "name": "Trailmix Theo", "platform": "YouTube", "category": "outdoor"},
    {"id": "summit_and_sea", "name": "Summit & Sea", "platform": "Instagram", "category": "outdoor"},
    {"id": "campfire_cara", "name": "Campfire Cara", "platform": "TikTok", "category": "outdoor"},
    {"id": "pantry_paloma", "name": "Pantry Paloma", "platform": "Instagram", "category": "home & kitchen"},
    {"id": "dermdaily_dee", "name": "DermDaily Dee", "platform": "TikTok", "category": "beauty"},
    {"id": "peaklife_priya", "name": "PeakLife Priya", "platform": "YouTube", "category": "activewear"},
    {"id": "wanderwell_wes", "name": "Wanderwell Wes", "platform": "Instagram", "category": "outdoor"},
]

TEAM_MEMBERS = [
    {"id": "jessica_moreno", "name": "Jessica Moreno", "role": "Senior Account Director"},
    {"id": "derek_holt", "name": "Derek Holt", "role": "Account Manager"},
    {"id": "priya_nair", "name": "Priya Nair", "role": "Account Manager"},
    {"id": "sam_okafor", "name": "Sam Okafor", "role": "Associate Account Manager"},
    {"id": "lena_bui", "name": "Lena Bui", "role": "Partnerships Lead"},
    {"id": "marcus_webb", "name": "Marcus Webb", "role": "Account Director"},
]

REASON_TEMPLATES = [
    "prior campaign showed repeated engagement lift but flat conversion",
    "client wanted lower fixed cost exposure after a soft quarter",
    "creator had two consecutive strong content cycles with growing audience",
    "attribution confidence was uncertain due to shared promo-code usage",
    "client's objective shifted toward new-customer acquisition",
    "prior flat-fee renewal underperformed relative to cost",
    "creator requested a rate increase the client wanted to de-risk",
    "commerce performance was promising but not yet verified independently",
]

RESULT_TEMPLATES_POSITIVE = [
    "verified revenue exceeded the prior period and cost efficiency improved",
    "new-customer share of attributed revenue increased materially",
    "engagement and conversion both improved versus the flat-fee baseline",
    "client renewed again the following cycle citing efficiency gains",
]

RESULT_TEMPLATES_NEGATIVE = [
    "performance bonus was not earned; verified revenue came in below target",
    "attribution remained ambiguous and the client paused the relationship",
    "engagement held but conversion did not improve versus baseline",
    "client reverted to flat-fee for the next cycle",
]

MONTHS = [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 8)]


def build_decisions():
    """31 comparable historical creator-renewal decisions.

    This is the exact comparable set backing the 'hybrid compensation beats
    flat-fee renewal under attribution uncertainty' pattern (evidence_count
    31, positive_outcomes 21). It is intentionally the full decision set for
    the prototype rather than a mix diluted with unrelated decision types -
    see spec Sec.5 ('do not overbuild').
    """
    decisions = []
    n = 31
    n_hybrid = 19
    n_flat = n - n_hybrid
    structures = ["hybrid_base_plus_performance"] * n_hybrid + ["flat_fee_renewal"] * n_flat
    random.shuffle(structures)

    # 21 of 31 positive overall, biased toward hybrid succeeding more often,
    # matching the pattern's headline stats (which are stored independently
    # on the pattern record as summary metrics, not re-derived from this list).
    positive_flags = [True] * 21 + [False] * (n - 21)
    random.shuffle(positive_flags)

    for i in range(n):
        client = random.choice(CLIENTS)
        creator = random.choice(CREATORS)
        owner = random.choice(TEAM_MEMBERS)
        structure = structures[i]
        positive = positive_flags[i]
        result_pool = RESULT_TEMPLATES_POSITIVE if positive else RESULT_TEMPLATES_NEGATIVE
        decisions.append({
            "id": f"pf_dec_{i+1:03d}",
            "client_id": client["id"],
            "creator_id": creator["id"],
            "decided_by": owner["id"],
            "date": random.choice(MONTHS),
            "compensation_structure": structure,
            "reason": random.choice(REASON_TEMPLATES),
            "outcome": "positive" if positive else "negative",
            "outcome_detail": random.choice(result_pool),
        })
    return decisions


def build_relationship_memories():
    memories = []
    pairs = set()
    templates = [
        ("negotiation_history", lambda tm, cr: f"{tm['name']} has negotiated with {cr['name']} on {random.choice([2,3,4])} prior occasions."),
        ("placement_requirement", lambda tm, cr: f"{cr['name']} historically requires premium placement guarantees before agreeing to renew."),
        ("responsiveness", lambda tm, cr: f"{cr['name']} typically responds within 48 hours and prefers structured performance offers."),
        ("relationship_owner", lambda tm, cr: f"{tm['name']} is the primary AP relationship owner for {cr['name']}."),
    ]
    while len(memories) < 14:
        tm = random.choice(TEAM_MEMBERS)
        cr = random.choice(CREATORS)
        key = (tm["id"], cr["id"])
        if key in pairs:
            continue
        pairs.add(key)
        predicate, template = random.choice(templates)
        memories.append({
            "id": f"pf_mem_rel_{len(memories)+1:03d}",
            "team_member_id": tm["id"],
            "creator_id": cr["id"],
            "predicate": predicate,
            "value": template(tm, cr),
        })
    return memories


def build_patterns(decisions):
    hybrid_decision_ids = [d["id"] for d in decisions]
    patterns = [
        {
            "id": "pattern_hybrid_comp",
            "name": "hybrid_beats_flat_fee_under_attribution_uncertainty",
            "predicate": "preferred_compensation_pattern",
            "value": "hybrid_base_plus_performance",
            "description": (
                "Hybrid creator compensation (base + performance) has outperformed flat-fee "
                "renewal in comparable creator-renewal decisions where prior commerce "
                "performance was promising but attribution confidence was uncertain."
            ),
            "evidence_count": 31,
            "positive_outcomes": 21,
            "flat_fee_success_rate": 0.41,
            "hybrid_success_rate": 0.68,
            "strongest_conditions": [
                "repeated prior performance",
                "new-customer objective",
                "controlled promo-code distribution",
                "verified performance outcome",
            ],
            "status": "approved_portfolio_pattern",
            "supporting_decision_ids": hybrid_decision_ids,
        },
        {
            "id": "pattern_bfcm_placement",
            "name": "bfcm_paid_placement_uplift",
            "predicate": "seasonal_placement_pattern",
            "value": "bfcm_paid_placements_outperform_baseline",
            "description": (
                "Paid placements booked with top affiliate publishers during BFCM have "
                "shown outsized revenue uplift versus the prior-month baseline across "
                "the portfolio."
            ),
            "evidence_count": 9,
            "positive_outcomes": 7,
            "flat_fee_success_rate": None,
            "hybrid_success_rate": None,
            "strongest_conditions": [
                "publisher already has an established relationship",
                "placement booked at least 3 weeks before BFCM",
            ],
            "status": "candidate_pattern",
            "supporting_decision_ids": [],
        },
        {
            "id": "pattern_coupon_concentration_risk",
            "name": "coupon_concentration_margin_risk",
            "predicate": "coupon_dependence_risk",
            "value": "high_coupon_concentration_correlates_with_margin_erosion",
            "description": (
                "Clients with high revenue concentration in coupon/loyalty publishers have "
                "shown gradual margin erosion versus clients with a more diversified "
                "publisher mix, across the portfolio."
            ),
            "evidence_count": 6,
            "positive_outcomes": None,
            "flat_fee_success_rate": None,
            "hybrid_success_rate": None,
            "strongest_conditions": [
                "coupon/loyalty share of attributed revenue above 40%",
            ],
            "status": "candidate_pattern",
            "supporting_decision_ids": [],
        },
    ]
    return patterns


def main():
    decisions = build_decisions()
    data = {
        "_synthetic": True,
        "_note": "All entities in this file are fictional and generated for the AP Intelligence Graph prototype. No real client, creator, or publisher data is represented.",
        "clients": CLIENTS,
        "creators": CREATORS,
        "team_members": TEAM_MEMBERS,
        "decisions": decisions,
        "relationship_memories": build_relationship_memories(),
        "patterns": build_patterns(decisions),
    }
    OUT_PATH.write_text(json.dumps(data, indent=2))
    print(f"wrote {OUT_PATH} ({len(decisions)} decisions, {len(data['relationship_memories'])} relationship memories, {len(data['patterns'])} patterns)")


if __name__ == "__main__":
    main()
