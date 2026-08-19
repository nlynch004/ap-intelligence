"""Pydantic schemas for API I/O.

`MemoryClaimOut` mirrors the claim schema from spec Sec.7 field-for-field.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ClaimStatus = Literal[
    "active", "superseded", "expired", "low_confidence", "needs_review", "rejected", "deprecated"
]
ClaimClass = Literal[
    "verified_fact",
    "account_preference",
    "historical_observation",
    "decision",
    "outcome",
    "hypothesis",
    "portfolio_pattern",
]
MemoryOperation = Literal[
    "CREATE", "UPDATE", "MERGE", "SUPERSEDE", "EXPIRE", "DEMOTE", "PROMOTE", "REJECT", "REQUEST_HUMAN_REVIEW"
]


class MemoryClaimOut(BaseModel):
    id: str
    type: str
    subject_type: str
    subject_id: str
    predicate: str
    value: str
    scope: dict[str, Any]
    claim_class: ClaimClass
    confidence: float
    authority_score: float
    source: dict[str, Any]
    valid_from: str
    valid_to: str | None
    status: ClaimStatus
    supersedes: list[str]
    superseded_by: str | None
    synthetic: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class CandidateClaimPayload(BaseModel):
    """What the extraction agent produces per candidate - a draft, not yet a full MemoryClaimOut."""

    type: str
    subject_type: str
    subject_id: str
    subject_label: str
    predicate: str
    value: str
    claim_class: ClaimClass
    confidence: float
    rationale: str = ""
    # Set deterministically by app.memory.manager (not by the LLM) - the
    # same value execute_create/execute_supersede will use as source.type
    # if this candidate is approved (spec Sec.18: review card should show
    # source, alongside claim/confidence/proposed operation).
    source_type: str = "account_team_statement"


class MemoryCandidateOut(BaseModel):
    id: str
    client_id: str
    claim_payload: CandidateClaimPayload
    proposed_operation: MemoryOperation
    conflict_with_claim_id: str | None
    conflict_with_claim: MemoryClaimOut | None = None
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


# ---- graph ----


class GraphNode(BaseModel):
    id: str
    node_type: Literal[
        "client", "creator", "publisher", "campaign", "team_member",
        "memory_claim", "decision", "outcome", "portfolio_pattern",
        "plan", "planned_action",
    ]
    label: str
    status: str | None = None
    data: dict[str, Any] = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ClientBriefResponse(BaseModel):
    client_id: str
    client_name: str
    active_memories: list[MemoryClaimOut]
    summary: str


# ---- chat ----


class ChatRequest(BaseModel):
    client_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    candidates: list[MemoryCandidateOut] = []
    referenced_memory_ids: list[str] = []
    recommendation: "RecommendationResponse | None" = None
    campaign_review: "CampaignReviewResponse | None" = None
    partner_brief: "PartnerBriefResponse | None" = None
    memory_history: "MemoryHistoryResponse | None" = None
    what_changed: "WhatChangedSummary | None" = None
    scenario_comparison: "ScenarioComparisonResponse | None" = None
    plan_proposal: "PlanProposalResponse | None" = None


# ---- memory review / conflicts ----


class MemoryReviewRequest(BaseModel):
    candidate_id: str
    action: Literal["approve", "reject"]


class MemoryReviewResponse(BaseModel):
    candidate_id: str
    operation_executed: MemoryOperation | None
    claim: MemoryClaimOut | None
    superseded_claim: MemoryClaimOut | None = None
    requires_conflict_resolution: bool = False
    conflict_with_claim: MemoryClaimOut | None = None


class ConflictResolveRequest(BaseModel):
    operation: MemoryOperation


class ConflictResolveResponse(BaseModel):
    new_claim: MemoryClaimOut | None = None
    superseded_claim: MemoryClaimOut | None = None


# ---- recommendations ----


class RecommendationRequest(BaseModel):
    client_id: str
    partner_id: str
    question: str


# ---- decision evidence ----
#
# Constructed deterministically in app/memory/retrieval.py from the same
# rows already retrieved for the recommendation context - the LLM never
# sees or produces this structure (spec Step 5). The frontend renders these
# fields directly; it must not parse `evidence_brief` prose to reconstruct
# them.


class CommercialAsk(BaseModel):
    proposed_fee: float | None
    prior_fee: float | None
    increase_pct: float | None  # (proposed - prior) / prior * 100, computed in Python


class CampaignPerformance(BaseModel):
    campaign_id: str
    month: str
    month_label: str
    fee: float | None
    attributed_revenue: float | None
    attributed_roas: float | None  # attributed_revenue / fee, computed in Python - not incremental/causal revenue
    link_clicks: int | None
    code_redemptions: int | None
    # Added for Phase 3 (Partner Brief spec: "engagement metrics already
    # present in the canonical campaign record" is a minimum requirement) -
    # also benefits Recommendation/Campaign Review, which reuse this same
    # type. Purely observational counts, never a brand-lift/causal claim.
    impressions: int | None = None
    engagements: int | None = None


class MeasurementCaution(BaseModel):
    claim_id: str
    claim_class: ClaimClass
    status: ClaimStatus
    confidence: float
    value: str
    summary: str  # deterministically assembled, not LLM-authored
    campaign_id: str | None = None
    link_clicks: int | None = None
    code_redemptions: int | None = None
    source_type: str | None = None


class ClientMemoryItem(BaseModel):
    claim_id: str
    predicate: str
    value: str
    claim_class: ClaimClass
    confidence: float


class PortfolioEvidence(BaseModel):
    pattern_id: str
    evidence_count: int
    positive_outcomes: int | None
    description: str
    synthetic: bool


class DecisionEvidence(BaseModel):
    commercial_ask: CommercialAsk
    prior_performance: list[CampaignPerformance]
    measurement_cautions: list[MeasurementCaution]
    client_memory: list[ClientMemoryItem]
    portfolio_evidence: PortfolioEvidence | None


class RecommendationResponse(BaseModel):
    client_id: str
    partner_id: str
    decision_evidence: DecisionEvidence
    recommendation: str
    recommended_terms: dict[str, Any]
    confidence: float
    supporting_memory_ids: list[str]
    uncertainties: list[str]
    explanation: str
    evidence_brief: str


# ---- campaign review (Phase 2) ----
#
# Same "deterministic evidence, then a bounded LLM call over exactly that
# evidence" shape as DecisionEvidence/RecommendationResponse above -
# constructed in app/memory/retrieval.py from actual retrieved DB rows,
# never produced or recomputed by the LLM. The review agent's own output
# (summary/what_worked/what_is_uncertain/planning_implications/
# candidate_lessons) is validated structured text and proposed lessons -
# never the metrics themselves, and never persisted directly (candidate
# lessons flow through the existing MemoryCandidate review pipeline).


class PriorCampaignComparison(BaseModel):
    has_prior: bool
    prior_month_label: str | None = None
    fee_delta: float | None = None
    fee_delta_pct: float | None = None
    revenue_delta: float | None = None
    revenue_delta_pct: float | None = None
    roas_delta: float | None = None  # this campaign's ROAS minus the prior campaign's, computed in Python


class PartnerMemoryItem(BaseModel):
    claim_id: str
    predicate: str
    value: str
    claim_class: ClaimClass
    confidence: float
    # Added for Phase 3 (Partner Brief needs source/status to distinguish
    # governed memory from structured source data in its own UI section);
    # populated for Campaign Review's use of this same type too, not just
    # a Partner-Brief-only field.
    status: ClaimStatus = "active"
    source: dict[str, Any] = {}


class CampaignReviewEvidence(BaseModel):
    campaign_id: str
    partner_id: str
    partner_name: str
    month: str
    month_label: str
    synthetic: bool
    fee: float | None
    attributed_revenue: float | None
    attributed_roas: float | None  # computed in Python, not incremental/causal revenue
    link_clicks: int | None
    code_redemptions: int | None
    # Creator/publisher-record metadata (platform notes etc.) - observed
    # source data the review may interpret, never itself governed memory
    # and never auto-persisted (spec Phase 2 requirement).
    partner_note: str | None = None
    client_memory: list[ClientMemoryItem]
    partner_memory: list[PartnerMemoryItem]
    measurement_cautions: list[MeasurementCaution]
    prior_campaign_comparison: PriorCampaignComparison


class CampaignReviewRequest(BaseModel):
    campaign_id: str


class CampaignReviewResponse(BaseModel):
    client_id: str
    partner_id: str
    campaign_id: str
    evidence: CampaignReviewEvidence
    summary: str
    what_worked: list[str]
    what_is_uncertain: list[str]
    planning_implications: list[str]
    candidate_lessons: list[MemoryCandidateOut]


# ---- partner brief (Phase 3) ----
#
# Same evidence-before-reasoning shape as Campaign Review: everything under
# PartnerBriefEvidence is retrieved/computed deterministically in
# app/memory/retrieval.py::build_partner_brief_context before the LLM is
# ever called. Phase 3 is read-only preparation, not a learning loop - there
# is deliberately no candidate_lessons field here (spec: "No new memory
# from Partner Brief yet").


class PartnerIdentity(BaseModel):
    partner_id: str
    name: str
    kind: str  # "creator" | "publisher"
    synthetic: bool
    platform: str | None = None
    follower_tier: str | None = None
    # Raw Partner-record metadata (structured source data from the seed/
    # system of record), deliberately NOT the same thing as a governed
    # relationship_status MemoryClaim - see PartnerBriefEvidence.
    # relationship_history below for the governed version, if one exists.
    record_relationship_status: str | None = None
    partner_note: str | None = None


class TeamExperienceItem(BaseModel):
    team_member_id: str
    name: str
    role: str
    # A recorded WORKED_WITH graph edge exists - nothing more. Deliberately
    # NOT "this person is the most experienced with this partner"; that
    # would require a documented negotiation_history claim (see
    # relationship_history), which this field intentionally does not imply.
    worked_with: bool


class CampaignPerformanceSummary(BaseModel):
    campaign_count: int
    most_recent_month_label: str | None = None
    most_recent_fee: float | None = None
    most_recent_roas: float | None = None
    average_roas: float | None = None  # mean over campaigns with a computable ROAS
    # mean(engagements / impressions) over campaigns with both present -
    # purely observational, never treated as evidence of brand lift.
    average_engagement_rate: float | None = None
    # (most recent fee - first fee) / first fee * 100 - the full history's
    # span, not a single-step delta (that's Campaign Review's job).
    fee_change_pct: float | None = None
    # "rising" | "falling" | "flat" | None (fewer than 2 campaigns) -
    # compares only the first and last campaign's attributed revenue, a
    # deliberately simple classification, not a fitted trend line.
    revenue_trend: str | None = None


class DecisionSummaryItem(BaseModel):
    decision_id: str
    summary: str
    terms: dict[str, Any]
    status: str
    motivated_by_claim_ids: list[str]
    created_at: str


class OutcomeSummaryItem(BaseModel):
    outcome_id: str
    decision_id: str
    metrics: dict[str, Any]
    outcome_label: str
    is_simulated: bool
    created_at: str


class PartnerBriefEvidence(BaseModel):
    partner: PartnerIdentity
    relationship_history: list[PartnerMemoryItem]
    team_experience: list[TeamExperienceItem]
    campaigns: list[CampaignPerformance]
    performance_stats: CampaignPerformanceSummary
    measurement_cautions: list[MeasurementCaution]
    client_context: list[ClientMemoryItem]
    prior_decisions: list[DecisionSummaryItem]
    outcomes: list[OutcomeSummaryItem]


class PartnerBriefRequest(BaseModel):
    partner_id: str
    client_id: str


class PartnerBriefResponse(BaseModel):
    client_id: str
    partner_id: str
    evidence: PartnerBriefEvidence
    relationship_summary: str
    performance_summary: str
    what_to_know: list[str]
    negotiation_considerations: list[str]
    measurement_considerations: list[str]
    open_questions: list[str]
    planning_implications: list[str] = []


# ---- memory history / "What Changed?" (Phase 4) ----
#
# A deliberately SEPARATE retrieval mode from every other workflow above.
# Those all call active_client_memories / active_partner_memories (status
# == "active" only) and must keep doing so unchanged. This section's
# queries are the only ones in the app allowed to return superseded/
# expired/needs_review claims - and only when a caller explicitly asks for
# history, never as a silent default.


class MemoryHistoryEntry(BaseModel):
    claim_id: str
    subject_type: str
    subject_id: str
    predicate: str
    value: str
    claim_class: ClaimClass
    status: ClaimStatus
    valid_from: str
    valid_to: str | None
    confidence: float
    authority_score: float
    source: dict[str, Any]
    supersedes: list[str]
    superseded_by: str | None
    synthetic: bool
    created_at: str


class MemoryHistorySubject(BaseModel):
    subject_type: str
    subject_id: str
    name: str


class MemoryHistoryTimeline(BaseModel):
    subject: MemoryHistorySubject
    predicate: str
    current_claim_id: str | None
    # Chronological (valid_from asc, then created_at asc) - see
    # app/memory/retrieval.py::build_memory_history. May contain a single
    # entry (a governed belief with no change history yet) - callers must
    # not treat len(changes) <= 1 as an error, just "nothing has changed."
    changes: list[MemoryHistoryEntry]


class MemoryHistoryRequest(BaseModel):
    subject_type: str
    subject_id: str
    predicate: str
    client_id: str | None = None


class MemoryHistoryResponse(BaseModel):
    timeline: MemoryHistoryTimeline
    # LLM-authored, optional narrative over the timeline above - never the
    # source of truth. Empty strings/lists when there's no real change to
    # narrate (single-entry timelines still get a plain "no change yet"
    # current_state line, never a fabricated evolution story).
    summary: str = ""
    material_changes: list[str] = []
    current_state: str = ""
    historical_context: list[str] = []


class ChangedDimension(BaseModel):
    """One entry in the broader 'what changed?' summary (spec Phase 4
    Sec.10) - deterministically found, not LLM-proposed."""

    subject_type: str
    subject_id: str
    subject_name: str
    predicate: str
    old_value: str
    new_value: str


class WhatChangedSummary(BaseModel):
    subject: MemoryHistorySubject
    changed_dimensions: list[ChangedDimension]


class WhatChangedRequest(BaseModel):
    subject_type: str
    subject_id: str
    client_id: str | None = None


# ---- scenario comparison (Phase 5) ----
#
# Same evidence-before-reasoning shape as every prior phase. The three
# RenewalScenario options and every qualitative rating in ScenarioAssessment
# are deterministically constructed in app/memory/scenario_rules.py before
# the LLM is ever called - the LLM only ever narrates the already-assessed
# set (schemas.ScenarioComparisonEvidence.model_dump()) and picks one of the
# supplied scenario ids as preferred. It never invents a scenario, never
# changes a rating, and never persists anything (spec Phase 5 Sec.20).


class RenewalScenario(BaseModel):
    id: str
    type: str  # "flat_fee" | "hybrid" | "do_not_renew"
    label: str
    base_fee: float
    performance_bonus_pct: float
    bonus_basis: str | None
    renews_relationship: bool


class ScenarioAssessment(BaseModel):
    scenario_id: str
    guaranteed_spend: float
    change_vs_latest_fee_pct: float | None  # application-calculated, never LLM-computed
    compensation_structure: str  # "Flat" | "Performance-linked" | "None"
    strategy_alignment: str  # "strong" | "moderate" | "weak" | "unknown"
    measurement_alignment: str  # "strong" | "moderate" | "weak" | "unknown"
    measurement_exposure: str  # "low" | "moderate" | "high" | "unknown"
    relationship_continuity: str  # "high" | "moderate" | "low"


class ScenarioWithAssessment(BaseModel):
    scenario: RenewalScenario
    assessment: ScenarioAssessment


class ScenarioComparisonEvidence(BaseModel):
    partner: PartnerIdentity
    campaigns: list[CampaignPerformance]
    performance_stats: CampaignPerformanceSummary
    # Scoped specifically to partnership_strategy / primary_growth_objective
    # / accepts_tradeoff (spec Sec.5) - narrower than Partner Brief's
    # broader client_context, and current-active-only like every other
    # workflow (superseded values never appear here - spec Sec.22).
    client_context: list[ClientMemoryItem]
    partner_memory: list[PartnerMemoryItem]
    measurement_cautions: list[MeasurementCaution]
    prior_decisions: list[DecisionSummaryItem]
    outcomes: list[OutcomeSummaryItem]
    current_ask: float
    scenarios: list[ScenarioWithAssessment]


class ScenarioComparisonRequest(BaseModel):
    client_id: str
    partner_id: str
    # Required, not optional - spec Sec.4: "Do not invent" a renewal ask.
    # The frontend collects this before calling the endpoint at all (an
    # inline "Current renewal ask" field); the bounded chat intent parses
    # one with the existing extract_dollar_amount helper and asks for it in
    # plain language if none is found, rather than calling this endpoint
    # without one.
    current_ask: float


class ScenarioComparisonResponse(BaseModel):
    client_id: str
    partner_id: str
    evidence: ScenarioComparisonEvidence
    preferred_scenario_id: str
    comparison_summary: str
    tradeoffs: list[str] = []
    uncertainties: list[str] = []
    questions_before_finalizing: list[str] = []
    confidence: float


# ---- decisions / outcomes ----


class DecisionCreateRequest(BaseModel):
    client_id: str
    partner_id: str
    summary: str
    terms: dict[str, Any]
    rationale: str
    motivated_by_claim_ids: list[str] = []
    # Optional (spec Phase 6 Sec.26) - set only when this decision fulfills a
    # specific approved PlannedAction. Never required, never inferred.
    source_planned_action_id: str | None = None


class DecisionOut(BaseModel):
    id: str
    client_id: str
    partner_id: str
    decision_type: str
    summary: str
    terms: dict[str, Any]
    rationale: str
    motivated_by_claim_ids: list[str]
    status: str
    synthetic: bool
    source_planned_action_id: str | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class OutcomeOut(BaseModel):
    id: str
    decision_id: str
    metrics: dict[str, Any]
    outcome_label: str
    is_simulated: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class SimulateOutcomeResponse(BaseModel):
    outcome: OutcomeOut
    pattern_id: str | None
    pattern_evidence_count_before: int | None
    pattern_evidence_count_after: int | None


# ---- account planning (Phase 6) ----
#
# Same evidence-before-reasoning shape as every prior phase, extended one
# step further: canonical DB state -> deterministic PlanningContext
# (app/memory/retrieval.py::build_planning_context, reusing the same
# active-only client-context rule and the same campaign/measurement-caution/
# partner-memory retrieval as Scenario Comparison and Partner Brief) ->
# bounded LLM proposal (app/agents/plan_agent.py) -> APPLICATION intersects
# every model-supplied id against the real evidence set, dropping anything
# invented (app/memory/planning_rules.py) -> PlanProposalResponse, which is
# API-response state ONLY, never written to the database -> human reviews
# and approves individual actions -> only then does
# app/memory/manager.py::create_plan persist a Plan + the approved
# PlannedActions. The two "proposed" schemas below (ProposedPlannedAction /
# PlanProposalResponse) are therefore deliberately separate types from the
# two persisted ones (PlannedActionOut / PlanOut) - spec Sec.29: "this
# protects the governance boundary."

PlannedActionType = Literal["renew", "renegotiate", "test", "expand", "pause", "review_measurement", "follow_up"]
PlannedActionStatus = Literal["approved", "in_progress", "completed", "cancelled"]
PlanStatus = Literal["draft", "approved", "active", "completed", "archived"]


class PlanningClientContext(BaseModel):
    client_id: str
    client_name: str
    # Active-only, scoped to the same 3 planning-relevant predicates Scenario
    # Comparison uses (retrieval.SCENARIO_CLIENT_PREDICATES) - never a
    # superseded value (spec Sec.32).
    current_strategy: list[ClientMemoryItem]


class ScenarioComparisonRef(BaseModel):
    """A previously-generated ScenarioComparisonResponse the user chose to
    carry into planning via "Use in plan" (spec Sec.16/35) - the frontend
    already holds this object in state from the Scenario Comparison call
    that produced it, and sends it back verbatim rather than the backend
    re-deriving it. Still defensively validated on arrival
    (app/memory/planning_rules.py::validate_scenario_inputs): partner_id
    must be a real partner in this PlanningContext and preferred_scenario_id
    must be one of the ids actually present in `scenarios` - this is
    app-originated data round-tripped through the client, not LLM output,
    but the boundary is checked anyway rather than trusted blindly."""

    partner_id: str
    preferred_scenario_id: str
    comparison_summary: str
    scenarios: list[ScenarioWithAssessment]


class PlanningExistingActionRef(BaseModel):
    """Compact view of an already-open PlannedAction, given to the planner
    so it does not casually propose a duplicate (spec Sec.9/31) - not the
    full PlannedActionOut shape, just enough to recognize an overlap."""

    id: str
    partner_id: str | None
    action_type: PlannedActionType
    summary: str
    status: PlannedActionStatus


class PlanningPartnerSummary(BaseModel):
    partner: PartnerIdentity
    campaigns: list[CampaignPerformance]
    performance_stats: CampaignPerformanceSummary
    measurement_cautions: list[MeasurementCaution]
    partner_memory: list[PartnerMemoryItem]
    # Only present if the caller passed a matching ScenarioComparisonRef for
    # this partner (spec Sec.35) - the strongest immediate planning input
    # when available, but plenty of partners will have none.
    scenario: ScenarioComparisonRef | None = None


class PlanningContext(BaseModel):
    """The full deterministic evidence object handed to propose_plan - see
    module note above. Explicitly labeled per spec Sec.9: everything under
    `client`/`partners`/`existing_decisions`/`existing_open_actions` is
    application-calculated/retrieved; only the eventual `plan_name`,
    `objective`, and `proposed_actions[].summary/rationale` in
    PlanProposalResponse are model-generated."""

    client: PlanningClientContext
    planning_period: str | None
    partners: list[PlanningPartnerSummary]
    existing_decisions: list[DecisionSummaryItem]
    existing_open_actions: list[PlanningExistingActionRef]


class ProposedPlannedAction(BaseModel):
    """One model-proposed action - API-response state only (spec Sec.29),
    never persisted directly. Every id here has already been intersected
    against PlanningContext by app/agents/plan_agent.py before this is
    constructed; the model never gets the final say on which ids survive."""

    temp_id: str  # e.g. "proposed_0" - stable within one proposal response only
    partner_id: str
    partner_name: str
    action_type: PlannedActionType
    summary: str
    rationale: str
    supporting_memory_ids: list[str] = []
    supporting_campaign_ids: list[str] = []
    source_scenario_id: str | None = None
    # Set deterministically (app/memory/planning_rules.py) when an existing
    # open PlannedAction already covers this same (partner_id, action_type) -
    # spec Sec.31: "visibly flagged as duplicate," not silently proposed.
    duplicate_of_planned_action_id: str | None = None


class PlanProposalResponse(BaseModel):
    client_id: str
    plan_name: str
    objective: str
    planning_period: str | None
    proposed_actions: list[ProposedPlannedAction]
    context: PlanningContext


class PlannedActionCreate(BaseModel):
    """One action the human has approved for persistence - the frontend
    builds this from a ProposedPlannedAction the user clicked Approve on,
    optionally with owner_id/due_date filled in manually (spec Sec.38:
    editable pre-persistence) - never with evidence fields changed."""

    partner_id: str | None = None
    campaign_id: str | None = None
    action_type: PlannedActionType
    summary: str
    rationale: str
    owner_id: str | None = None
    due_date: str | None = None
    supporting_memory_ids: list[str] = []
    supporting_campaign_ids: list[str] = []
    source_scenario_id: str | None = None


class PlanCreateRequest(BaseModel):
    client_id: str
    name: str
    planning_period: str | None = None
    objective: str
    actions: list[PlannedActionCreate] = []


class PlannedActionOut(BaseModel):
    id: str
    plan_id: str
    client_id: str
    partner_id: str | None
    partner_name: str | None = None
    campaign_id: str | None
    action_type: str
    summary: str
    rationale: str
    owner_id: str | None
    owner_name: str | None = None
    due_date: str | None
    status: str
    supporting_memory_ids: list[str]
    supporting_campaign_ids: list[str]
    source_scenario_id: str | None
    source_decision_id: str | None
    synthetic: bool
    created_at: str
    updated_at: str


class PlanOut(BaseModel):
    id: str
    client_id: str
    name: str
    planning_period: str | None
    objective: str
    status: str
    synthetic: bool
    created_at: str
    updated_at: str
    actions: list[PlannedActionOut] = []


class PlanCreateResponse(BaseModel):
    plan: PlanOut
    # Summaries of proposed actions that were requested but silently
    # skipped because a duplicate open action already existed (spec Sec.31:
    # "do not silently create duplicates" - reported back, not hidden).
    skipped_duplicate_actions: list[str] = []


class PlannedActionUpdate(BaseModel):
    status: PlannedActionStatus | None = None
    owner_id: str | None = None
    due_date: str | None = None
    summary: str | None = None


class PlanUpdate(BaseModel):
    status: PlanStatus


class PlanProposeRequest(BaseModel):
    client_id: str
    planning_period: str | None = None
    # None = every partner with campaign history for this client (spec
    # Sec.10) - never every partner in the system.
    partner_ids: list[str] | None = None
    scenario_inputs: list[ScenarioComparisonRef] = []


# ---- activity ----


class ActivityEventOut(BaseModel):
    id: str
    event_type: str
    summary: str
    detail: dict[str, Any]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


ChatResponse.model_rebuild()
