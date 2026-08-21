import type {
  CampaignReviewResponse,
  ChatResponse,
  ClientBrief,
  ClientSummary,
  ConflictResolveResponse,
  DemoResetResponse,
  GraphResponse,
  MemoryHistoryResponse,
  MemoryOperation,
  MemoryReviewResponse,
  ActivityEvent,
  Decision,
  PartnerBriefResponse,
  PlanCreateRequest,
  PlanCreateResponse,
  PlanOut,
  PlanProposalResponse,
  PlannedActionOut,
  PlannedActionUpdate,
  PlanUpdate,
  ScenarioComparisonRef,
  ScenarioComparisonResponse,
  SimulateOutcomeResponse,
  WhatChangedSummary,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function adminToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )ap_admin_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = adminToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Admin-Password": token } : {}),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${init?.method || "GET"} ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listClients: () => request<ClientSummary[]>("/api/clients"),

  getGraph: (clientId: string) => request<GraphResponse>(`/api/clients/${clientId}/graph`),

  getBrief: (clientId: string) => request<ClientBrief>(`/api/clients/${clientId}/brief`),

  getActivity: (clientId: string) => request<ActivityEvent[]>(`/api/clients/${clientId}/activity`),

  sendChat: (clientId: string, message: string) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ client_id: clientId, message }),
    }),

  reviewMemory: (candidateId: string, action: "approve" | "reject") =>
    request<MemoryReviewResponse>("/api/memories/review", {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId, action }),
    }),

  resolveConflict: (conflictId: string, operation: MemoryOperation) =>
    request<ConflictResolveResponse>(`/api/memories/conflicts/${conflictId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ operation }),
    }),

  reviewCampaign: (campaignId: string) =>
    request<CampaignReviewResponse>("/api/campaign-review", {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId }),
    }),

  getPartnerBrief: (partnerId: string, clientId: string) =>
    request<PartnerBriefResponse>("/api/partner-brief", {
      method: "POST",
      body: JSON.stringify({ partner_id: partnerId, client_id: clientId }),
    }),

  getMemoryHistory: (subjectType: string, subjectId: string, predicate: string, clientId?: string) =>
    request<MemoryHistoryResponse>("/api/memory-history", {
      method: "POST",
      body: JSON.stringify({ subject_type: subjectType, subject_id: subjectId, predicate, client_id: clientId ?? null }),
    }),

  getWhatChanged: (subjectType: string, subjectId: string, clientId?: string) =>
    request<WhatChangedSummary>("/api/memory-history/what-changed", {
      method: "POST",
      body: JSON.stringify({ subject_type: subjectType, subject_id: subjectId, client_id: clientId ?? null }),
    }),

  compareScenarios: (partnerId: string, clientId: string, currentAsk: number) =>
    request<ScenarioComparisonResponse>("/api/scenario-comparison", {
      method: "POST",
      body: JSON.stringify({ partner_id: partnerId, client_id: clientId, current_ask: currentAsk }),
    }),

  createDecision: (payload: {
    client_id: string;
    partner_id: string;
    summary: string;
    terms: Record<string, unknown>;
    rationale: string;
    motivated_by_claim_ids: string[];
    source_planned_action_id?: string | null;
  }) => request<Decision>("/api/decisions", { method: "POST", body: JSON.stringify(payload) }),

  proposePlan: (clientId: string, opts?: { planningPeriod?: string | null; partnerIds?: string[] | null; scenarioInputs?: ScenarioComparisonRef[] }) =>
    request<PlanProposalResponse>("/api/plans/propose", {
      method: "POST",
      body: JSON.stringify({
        client_id: clientId,
        planning_period: opts?.planningPeriod ?? null,
        partner_ids: opts?.partnerIds ?? null,
        scenario_inputs: opts?.scenarioInputs ?? [],
      }),
    }),

  createPlan: (payload: PlanCreateRequest) => request<PlanCreateResponse>("/api/plans", { method: "POST", body: JSON.stringify(payload) }),

  listPlans: (clientId: string) => request<PlanOut[]>(`/api/clients/${clientId}/plans`),

  updatePlan: (planId: string, patch: PlanUpdate) =>
    request<PlanOut>(`/api/plans/${planId}`, { method: "PATCH", body: JSON.stringify(patch) }),

  updatePlannedAction: (actionId: string, patch: PlannedActionUpdate) =>
    request<PlannedActionOut>(`/api/planned-actions/${actionId}`, { method: "PATCH", body: JSON.stringify(patch) }),

  simulateOutcome: (decisionId: string) =>
    request<SimulateOutcomeResponse>(`/api/decisions/${decisionId}/simulate-outcome`, { method: "POST" }),

  resetDemo: () => request<DemoResetResponse>("/api/demo/reset", { method: "POST" }),
};
