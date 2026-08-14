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
  | "portfolio_pattern";

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

export interface RecommendationResponse {
  client_id: string;
  partner_id: string;
  recommendation: string;
  recommended_terms: { base_fee: number; performance_bonus_pct: number; bonus_basis: string; [k: string]: unknown };
  confidence: number;
  supporting_memory_ids: string[];
  uncertainties: string[];
  explanation: string;
  evidence_brief: string;
}

export interface ChatResponse {
  reply: string;
  candidates: MemoryCandidate[];
  referenced_memory_ids: string[];
  recommendation: RecommendationResponse | null;
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
