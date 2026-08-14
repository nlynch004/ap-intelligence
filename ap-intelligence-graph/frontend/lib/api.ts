import type {
  ChatResponse,
  ClientBrief,
  ClientSummary,
  ConflictResolveResponse,
  GraphResponse,
  MemoryOperation,
  MemoryReviewResponse,
  ActivityEvent,
  Decision,
  SimulateOutcomeResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
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

  createDecision: (payload: {
    client_id: string;
    partner_id: string;
    summary: string;
    terms: Record<string, unknown>;
    rationale: string;
    motivated_by_claim_ids: string[];
  }) => request<Decision>("/api/decisions", { method: "POST", body: JSON.stringify(payload) }),

  simulateOutcome: (decisionId: string) =>
    request<SimulateOutcomeResponse>(`/api/decisions/${decisionId}/simulate-outcome`, { method: "POST" }),
};
