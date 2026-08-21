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

    type: str
    subject_type: str
    subject_id: str
    subject_label: str
    predicate: str
    value: str
    claim_class: ClaimClass
    confidence: float
    rationale: str = ""
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


class RecommendationRequest(BaseModel):
    client_id: str
    partner_id: str
    question: str


class CommercialAsk(BaseModel):
    proposed_fee: float | None
    prior_fee: float | None
    increase_pct: float | None


class CampaignPerformance(BaseModel):
    campaign_id: str
    month: str
    month_label: str
    fee: float | None
    attributed_revenue: float | None
    attributed_roas: float | None
    link_clicks: int | None
    code_redemptions: int | None
    impressions: int | None = None
    engagements: int | None = None


class MeasurementCaution(BaseModel):
    claim_id: str
    claim_class: ClaimClass
    status: ClaimStatus
    confidence: float
    value: str
    summary: str
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


class PriorCampaignComparison(BaseModel):
    has_prior: bool
    prior_month_label: str | None = None
    fee_delta: float | None = None
    fee_delta_pct: float | None = None
    revenue_delta: float | None = None
    revenue_delta_pct: float | None = None
    roas_delta: float | None = None


class PartnerMemoryItem(BaseModel):
    claim_id: str
    predicate: str
    value: str
    claim_class: ClaimClass
    confidence: float
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
    attributed_roas: float | None
    link_clicks: int | None
    code_redemptions: int | None
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


class PartnerIdentity(BaseModel):
    partner_id: str
    name: str
    kind: str
    synthetic: bool
    platform: str | None = None
    follower_tier: str | None = None
    record_relationship_status: str | None = None
    partner_note: str | None = None


class TeamExperienceItem(BaseModel):
    team_member_id: str
    name: str
    role: str
    worked_with: bool


class CampaignPerformanceSummary(BaseModel):
    campaign_count: int
    most_recent_month_label: str | None = None
    most_recent_fee: float | None = None
    most_recent_roas: float | None = None
    average_roas: float | None = None
    average_engagement_rate: float | None = None
    fee_change_pct: float | None = None
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
    changes: list[MemoryHistoryEntry]


class MemoryHistoryRequest(BaseModel):
    subject_type: str
    subject_id: str
    predicate: str
    client_id: str | None = None


class MemoryHistoryResponse(BaseModel):
    timeline: MemoryHistoryTimeline
    summary: str = ""
    material_changes: list[str] = []
    current_state: str = ""
    historical_context: list[str] = []


class ChangedDimension(BaseModel):

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


class RenewalScenario(BaseModel):
    id: str
    type: str
    label: str
    base_fee: float
    performance_bonus_pct: float
    bonus_basis: str | None
    renews_relationship: bool


class ScenarioAssessment(BaseModel):
    scenario_id: str
    guaranteed_spend: float
    change_vs_latest_fee_pct: float | None
    compensation_structure: str
    strategy_alignment: str
    measurement_alignment: str
    measurement_exposure: str
    relationship_continuity: str


class ScenarioWithAssessment(BaseModel):
    scenario: RenewalScenario
    assessment: ScenarioAssessment


class ScenarioComparisonEvidence(BaseModel):
    partner: PartnerIdentity
    campaigns: list[CampaignPerformance]
    performance_stats: CampaignPerformanceSummary
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


class DecisionCreateRequest(BaseModel):
    client_id: str
    partner_id: str
    summary: str
    terms: dict[str, Any]
    rationale: str
    motivated_by_claim_ids: list[str] = []
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


PlannedActionType = Literal["renew", "renegotiate", "test", "expand", "pause", "review_measurement", "follow_up"]
PlannedActionStatus = Literal["approved", "in_progress", "completed", "cancelled"]
PlanStatus = Literal["draft", "approved", "active", "completed", "archived"]


class PlanningClientContext(BaseModel):
    client_id: str
    client_name: str
    current_strategy: list[ClientMemoryItem]


class ScenarioComparisonRef(BaseModel):

    partner_id: str
    preferred_scenario_id: str
    comparison_summary: str
    scenarios: list[ScenarioWithAssessment]


class PlanningExistingActionRef(BaseModel):

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
    scenario: ScenarioComparisonRef | None = None


class PlanningContext(BaseModel):

    client: PlanningClientContext
    planning_period: str | None
    partners: list[PlanningPartnerSummary]
    existing_decisions: list[DecisionSummaryItem]
    existing_open_actions: list[PlanningExistingActionRef]


class ProposedPlannedAction(BaseModel):

    temp_id: str
    partner_id: str
    partner_name: str
    action_type: PlannedActionType
    summary: str
    rationale: str
    supporting_memory_ids: list[str] = []
    supporting_campaign_ids: list[str] = []
    source_scenario_id: str | None = None
    duplicate_of_planned_action_id: str | None = None


class PlanProposalResponse(BaseModel):
    client_id: str
    plan_name: str
    objective: str
    planning_period: str | None
    proposed_actions: list[ProposedPlannedAction]
    context: PlanningContext


class PlannedActionCreate(BaseModel):

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
    partner_ids: list[str] | None = None
    scenario_inputs: list[ScenarioComparisonRef] = []


class ActivityEventOut(BaseModel):
    id: str
    event_type: str
    summary: str
    detail: dict[str, Any]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


ChatResponse.model_rebuild()
