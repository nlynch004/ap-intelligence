// Mirrors backend/app/schemas.py. Kept hand-in-sync deliberately (no codegen)
// since the API surface is small and stable for the prototype.

export type ClaimStatus =
  | "active"
  | "superseded"
  | "expired"
  | "low_confidence"
  | "needs_review"
  | "rejected"
  | "deprecated";

export type ClaimClass =
  | "verified_fact"
  | "account_preference"
  | "historical_observation"
  | "decision"
  | "outcome"
  | "hypothesis"
  | "portfolio_pattern";

export type MemoryOperation =
  | "CREATE"
  | "UPDATE"
  | "MERGE"
  | "SUPERSEDE"
  | "EXPIRE"
  | "DEMOTE"
  | "PROMOTE"
  | "REJECT"
  | "REQUEST_HUMAN_REVIEW";

export interface MemoryClaim {
  id: string;
  type: string;
  subject_type: string;
  subject_id: string;
  predicate: string;
  value: string;
  scope: Record<string, unknown>;
  claim_class: ClaimClass;
  confidence: number;
  authority_score: number;
  source: { type: string; source_id?: string; speaker?: string | null; [k: string]: unknown };
  valid_from: string;
  valid_to: string | null;
  status: ClaimStatus;
  supersedes: string[];
  superseded_by: string | null;
  synthetic: boolean;
  created_at: string;
}

export interface CandidateClaimPayload {
  type: string;
  subject_type: string;
  subject_id: string;
  subject_label: string;
  predicate: string;
  value: string;
  claim_class: ClaimClass;
  confidence: number;
  rationale: string;
  source_type: string;
}

export interface MemoryCandidate {
  id: string;
  client_id: string;
  claim_payload: CandidateClaimPayload;
  proposed_operation: MemoryOperation;
  conflict_with_claim_id: string | null;
  conflict_with_claim: MemoryClaim | null;
  status: string;
  created_at: string;
}

export type GraphNodeType =
  | "client"
  | "creator"
  | "publisher"
  | "campaign"
  | "team_member"
  | "memory_claim"
  | "decision"
  | "outcome"
  | "portfolio_pattern"
  | "plan"
  | "planned_action";

export interface GraphNodeData {
  id: string;
  node_type: GraphNodeType;
  label: string;
  status: string | null;
  data: Record<string, unknown>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  relationship: string;
}

export interface GraphResponse {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}

export interface ClientBrief {
  client_id: string;
  client_name: string;
  active_memories: MemoryClaim[];
  summary: string;
}

// Constructed deterministically on the backend from retrieved DB rows - see
// backend/app/memory/retrieval.py. The frontend renders these fields
// directly; it must never parse `evidence_brief` prose to reconstruct them.
export interface CommercialAsk {
  proposed_fee: number | null;
  prior_fee: number | null;
  increase_pct: number | null;
}

export interface CampaignPerformance {
  campaign_id: string;
  month: string;
  month_label: string;
  fee: number | null;
  attributed_revenue: number | null;
  attributed_roas: number | null;
  link_clicks: number | null;
  code_redemptions: number | null;
  impressions: number | null;
  engagements: number | null;
}

export interface MeasurementCaution {
  claim_id: string;
  claim_class: ClaimClass;
  status: ClaimStatus;
  confidence: number;
  value: string;
  summary: string;
  campaign_id: string | null;
  link_clicks: number | null;
  code_redemptions: number | null;
  source_type: string | null;
}

export interface ClientMemoryItem {
  claim_id: string;
  predicate: string;
  value: string;
  claim_class: ClaimClass;
  confidence: number;
}

export interface PortfolioEvidence {
  pattern_id: string;
  evidence_count: number;
  positive_outcomes: number | null;
  description: string;
  synthetic: boolean;
}

export interface DecisionEvidence {
  commercial_ask: CommercialAsk;
  prior_performance: CampaignPerformance[];
  measurement_cautions: MeasurementCaution[];
  client_memory: ClientMemoryItem[];
  portfolio_evidence: PortfolioEvidence | null;
}

export interface RecommendationResponse {
  client_id: string;
  partner_id: string;
  decision_evidence: DecisionEvidence;
  recommendation: string;
  recommended_terms: { base_fee: number; performance_bonus_pct: number; bonus_basis: string; [k: string]: unknown };
  confidence: number;
  supporting_memory_ids: string[];
  uncertainties: string[];
  explanation: string;
  evidence_brief: string;
}

// Constructed deterministically on the backend from retrieved DB rows - see
// backend/app/memory/retrieval.py::build_campaign_review_context. The
// frontend renders these fields directly; the LLM only ever sees this
// object and never recomputes any of it.
export interface PriorCampaignComparison {
  has_prior: boolean;
  prior_month_label: string | null;
  fee_delta: number | null;
  fee_delta_pct: number | null;
  revenue_delta: number | null;
  revenue_delta_pct: number | null;
  roas_delta: number | null;
}

export interface PartnerMemoryItem {
  claim_id: string;
  predicate: string;
  value: string;
  claim_class: ClaimClass;
  confidence: number;
  status: ClaimStatus;
  source: { type: string; [k: string]: unknown };
}

export interface CampaignReviewEvidence {
  campaign_id: string;
  partner_id: string;
  partner_name: string;
  month: string;
  month_label: string;
  synthetic: boolean;
  fee: number | null;
  attributed_revenue: number | null;
  attributed_roas: number | null;
  link_clicks: number | null;
  code_redemptions: number | null;
  partner_note: string | null;
  client_memory: ClientMemoryItem[];
  partner_memory: PartnerMemoryItem[];
  measurement_cautions: MeasurementCaution[];
  prior_campaign_comparison: PriorCampaignComparison;
}

export interface CampaignReviewResponse {
  client_id: string;
  partner_id: string;
  campaign_id: string;
  evidence: CampaignReviewEvidence;
  summary: string;
  what_worked: string[];
  what_is_uncertain: string[];
  planning_implications: string[];
  candidate_lessons: MemoryCandidate[];
}

// Constructed deterministically on the backend from retrieved DB rows - see
// backend/app/memory/retrieval.py::build_partner_brief_context.
export interface PartnerIdentity {
  partner_id: string;
  name: string;
  kind: string;
  synthetic: boolean;
  platform: string | null;
  follower_tier: string | null;
  record_relationship_status: string | null;
  partner_note: string | null;
}

export interface TeamExperienceItem {
  team_member_id: string;
  name: string;
  role: string;
  worked_with: boolean;
}

export interface CampaignPerformanceSummary {
  campaign_count: number;
  most_recent_month_label: string | null;
  most_recent_fee: number | null;
  most_recent_roas: number | null;
  average_roas: number | null;
  average_engagement_rate: number | null;
  fee_change_pct: number | null;
  revenue_trend: string | null;
}

export interface DecisionSummaryItem {
  decision_id: string;
  summary: string;
  terms: Record<string, unknown>;
  status: string;
  motivated_by_claim_ids: string[];
  created_at: string;
}

export interface OutcomeSummaryItem {
  outcome_id: string;
  decision_id: string;
  metrics: Record<string, unknown>;
  outcome_label: string;
  is_simulated: boolean;
  created_at: string;
}

export interface PartnerBriefEvidence {
  partner: PartnerIdentity;
  relationship_history: PartnerMemoryItem[];
  team_experience: TeamExperienceItem[];
  campaigns: CampaignPerformance[];
  performance_stats: CampaignPerformanceSummary;
  measurement_cautions: MeasurementCaution[];
  client_context: ClientMemoryItem[];
  prior_decisions: DecisionSummaryItem[];
  outcomes: OutcomeSummaryItem[];
}

export interface PartnerBriefResponse {
  client_id: string;
  partner_id: string;
  evidence: PartnerBriefEvidence;
  relationship_summary: string;
  performance_summary: string;
  what_to_know: string[];
  negotiation_considerations: string[];
  measurement_considerations: string[];
  open_questions: string[];
  planning_implications: string[];
}

// Constructed deterministically on the backend from retrieved DB rows - see
// backend/app/memory/retrieval.py::build_memory_history. A deliberately
// separate retrieval mode from every other *Evidence type above - this is
// the only one allowed to include superseded/needs_review claims.
export interface MemoryHistoryEntry {
  claim_id: string;
  subject_type: string;
  subject_id: string;
  predicate: string;
  value: string;
  claim_class: ClaimClass;
  status: ClaimStatus;
  valid_from: string;
  valid_to: string | null;
  confidence: number;
  authority_score: number;
  source: { type: string; [k: string]: unknown };
  supersedes: string[];
  superseded_by: string | null;
  synthetic: boolean;
  created_at: string;
}

export interface MemoryHistorySubject {
  subject_type: string;
  subject_id: string;
  name: string;
}

export interface MemoryHistoryTimeline {
  subject: MemoryHistorySubject;
  predicate: string;
  current_claim_id: string | null;
  changes: MemoryHistoryEntry[];
}

export interface MemoryHistoryResponse {
  timeline: MemoryHistoryTimeline;
  summary: string;
  material_changes: string[];
  current_state: string;
  historical_context: string[];
}

export interface ChangedDimension {
  subject_type: string;
  subject_id: string;
  subject_name: string;
  predicate: string;
  old_value: string;
  new_value: string;
}

export interface WhatChangedSummary {
  subject: MemoryHistorySubject;
  changed_dimensions: ChangedDimension[];
}

// Constructed deterministically on the backend from retrieved DB rows - see
// backend/app/memory/scenario_rules.py + retrieval.py::build_scenario_comparison_context.
// The LLM only ever narrates/chooses among these; it never builds or
// re-rates them.
export interface RenewalScenario {
  id: string;
  type: string; // "flat_fee" | "hybrid" | "do_not_renew"
  label: string;
  base_fee: number;
  performance_bonus_pct: number;
  bonus_basis: string | null;
  renews_relationship: boolean;
}

export interface ScenarioAssessment {
  scenario_id: string;
  guaranteed_spend: number;
  change_vs_latest_fee_pct: number | null;
  compensation_structure: string;
  strategy_alignment: string;
  measurement_alignment: string;
  measurement_exposure: string;
  relationship_continuity: string;
}

export interface ScenarioWithAssessment {
  scenario: RenewalScenario;
  assessment: ScenarioAssessment;
}

export interface ScenarioComparisonEvidence {
  partner: PartnerIdentity;
  campaigns: CampaignPerformance[];
  performance_stats: CampaignPerformanceSummary;
  client_context: ClientMemoryItem[];
  partner_memory: PartnerMemoryItem[];
  measurement_cautions: MeasurementCaution[];
  prior_decisions: DecisionSummaryItem[];
  outcomes: OutcomeSummaryItem[];
  current_ask: number;
  scenarios: ScenarioWithAssessment[];
}

export interface ScenarioComparisonResponse {
  client_id: string;
  partner_id: string;
  evidence: ScenarioComparisonEvidence;
  preferred_scenario_id: string;
  comparison_summary: string;
  tradeoffs: string[];
  uncertainties: string[];
  questions_before_finalizing: string[];
  confidence: number;
}

// Constructed deterministically on the backend from retrieved DB rows - see
// backend/app/memory/retrieval.py::build_planning_context. See
// PlanProposalResponse below for the full "proposed, never persisted"
// governance boundary.
export interface PlanningClientContext {
  client_id: string;
  client_name: string;
  current_strategy: ClientMemoryItem[];
}

// A previously-generated ScenarioComparisonResponse carried into planning
// via "Use in plan" - see ScenarioComparisonPanel's onUseInPlan.
export interface ScenarioComparisonRef {
  partner_id: string;
  preferred_scenario_id: string;
  comparison_summary: string;
  scenarios: ScenarioWithAssessment[];
}

export interface PlanningExistingActionRef {
  id: string;
  partner_id: string | null;
  action_type: PlannedActionType;
  summary: string;
  status: PlannedActionStatus;
}

export interface PlanningPartnerSummary {
  partner: PartnerIdentity;
  campaigns: CampaignPerformance[];
  performance_stats: CampaignPerformanceSummary;
  measurement_cautions: MeasurementCaution[];
  partner_memory: PartnerMemoryItem[];
  scenario: ScenarioComparisonRef | null;
}

export interface PlanningContext {
  client: PlanningClientContext;
  planning_period: string | null;
  partners: PlanningPartnerSummary[];
  existing_decisions: DecisionSummaryItem[];
  existing_open_actions: PlanningExistingActionRef[];
}

export type PlannedActionType = "renew" | "renegotiate" | "test" | "expand" | "pause" | "review_measurement" | "follow_up";
export type PlannedActionStatus = "approved" | "in_progress" | "completed" | "cancelled";
export type PlanStatus = "draft" | "approved" | "active" | "completed" | "archived";

// API-response state only (spec Phase 6 Sec.29) - never itself persisted.
// Every id here has already been intersected against PlanningContext by the
// backend (app/agents/plan_agent.py + app/memory/planning_rules.py) before
// this reaches the frontend.
export interface ProposedPlannedAction {
  temp_id: string;
  partner_id: string;
  partner_name: string;
  action_type: PlannedActionType;
  summary: string;
  rationale: string;
  supporting_memory_ids: string[];
  supporting_campaign_ids: string[];
  source_scenario_id: string | null;
  duplicate_of_planned_action_id: string | null;
}

export interface PlanProposalResponse {
  client_id: string;
  plan_name: string;
  objective: string;
  planning_period: string | null;
  proposed_actions: ProposedPlannedAction[];
  context: PlanningContext;
}

export interface PlannedActionCreate {
  partner_id?: string | null;
  campaign_id?: string | null;
  action_type: PlannedActionType;
  summary: string;
  rationale: string;
  owner_id?: string | null;
  due_date?: string | null;
  supporting_memory_ids?: string[];
  supporting_campaign_ids?: string[];
  source_scenario_id?: string | null;
}

export interface PlanCreateRequest {
  client_id: string;
  name: string;
  planning_period?: string | null;
  objective: string;
  actions: PlannedActionCreate[];
}

// Persisted, canonical state - see PlanProposalResponse above for the
// deliberately separate ephemeral/proposed counterpart of this type.
export interface PlannedActionOut {
  id: string;
  plan_id: string;
  client_id: string;
  partner_id: string | null;
  partner_name: string | null;
  campaign_id: string | null;
  action_type: string;
  summary: string;
  rationale: string;
  owner_id: string | null;
  owner_name: string | null;
  due_date: string | null;
  status: string;
  supporting_memory_ids: string[];
  supporting_campaign_ids: string[];
  source_scenario_id: string | null;
  source_decision_id: string | null;
  synthetic: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlanOut {
  id: string;
  client_id: string;
  name: string;
  planning_period: string | null;
  objective: string;
  status: string;
  synthetic: boolean;
  created_at: string;
  updated_at: string;
  actions: PlannedActionOut[];
}

export interface PlanCreateResponse {
  plan: PlanOut;
  skipped_duplicate_actions: string[];
}

export interface PlannedActionUpdate {
  status?: PlannedActionStatus;
  owner_id?: string | null;
  due_date?: string | null;
  summary?: string;
}

export interface PlanUpdate {
  status: PlanStatus;
}

export interface ChatResponse {
  reply: string;
  candidates: MemoryCandidate[];
  referenced_memory_ids: string[];
  recommendation: RecommendationResponse | null;
  campaign_review: CampaignReviewResponse | null;
  partner_brief: PartnerBriefResponse | null;
  memory_history: MemoryHistoryResponse | null;
  what_changed: WhatChangedSummary | null;
  scenario_comparison: ScenarioComparisonResponse | null;
  plan_proposal: PlanProposalResponse | null;
}

export interface MemoryReviewResponse {
  candidate_id: string;
  operation_executed: MemoryOperation | null;
  claim: MemoryClaim | null;
  superseded_claim: MemoryClaim | null;
  requires_conflict_resolution: boolean;
  conflict_with_claim: MemoryClaim | null;
}

export interface ConflictResolveResponse {
  new_claim: MemoryClaim | null;
  superseded_claim: MemoryClaim | null;
}

export interface Decision {
  id: string;
  client_id: string;
  partner_id: string;
  decision_type: string;
  summary: string;
  terms: Record<string, unknown>;
  rationale: string;
  motivated_by_claim_ids: string[];
  status: string;
  synthetic: boolean;
  created_at: string;
}

export interface Outcome {
  id: string;
  decision_id: string;
  metrics: Record<string, unknown>;
  outcome_label: string;
  is_simulated: boolean;
  created_at: string;
}

export interface SimulateOutcomeResponse {
  outcome: Outcome;
  pattern_id: string | null;
  pattern_evidence_count_before: number | null;
  pattern_evidence_count_after: number | null;
}

export interface ActivityEvent {
  id: string;
  event_type: string;
  summary: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface ClientSummary {
  id: string;
  name: string;
  industry: string | null;
  synthetic: boolean;
}

export interface Partner {
  id: string;
  name: string;
}

// Demo-only - see backend/app/routers/demo.py.
export interface DemoResetResponse {
  status: string;
  demo_only: boolean;
  message: string;
}
