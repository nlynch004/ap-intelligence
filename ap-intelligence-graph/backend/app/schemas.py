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


# ---- decisions / outcomes ----


class DecisionCreateRequest(BaseModel):
    client_id: str
    partner_id: str
    summary: str
    terms: dict[str, Any]
    rationale: str
    motivated_by_claim_ids: list[str] = []


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


# ---- activity ----


class ActivityEventOut(BaseModel):
    id: str
    event_type: str
    summary: str
    detail: dict[str, Any]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


ChatResponse.model_rebuild()
