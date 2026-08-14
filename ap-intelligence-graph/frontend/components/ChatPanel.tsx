"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  Decision,
  GraphResponse,
  MemoryCandidate,
  MemoryClaim,
  RecommendationResponse,
  SimulateOutcomeResponse,
} from "@/lib/types";
import { CandidateMemoryReview } from "./CandidateMemoryReview";
import { ConflictDialog } from "./ConflictDialog";
import { RecommendationCard } from "./RecommendationCard";

type Msg =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string }
  | { id: string; role: "candidates"; candidates: MemoryCandidate[] }
  | { id: string; role: "recommendation"; recommendation: RecommendationResponse };

const SUGGESTIONS = [
  "Bring me up to speed on Northwind.",
  "Northwind's strategy changed after last week's executive review. They now want to reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS is a little lower.",
  "Summit Sisters wants $6,000 for another campaign. Should we renew them?",
];

let uid = 0;
const nextId = () => `m${++uid}_${Date.now()}`;

export function ChatPanel({
  clientId,
  graph,
  onAfterMutation,
  onHighlight,
}: {
  clientId: string;
  graph: GraphResponse | null;
  onAfterMutation: () => void;
  onHighlight: (ids: string[]) => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [resolved, setResolved] = useState<Record<string, "approved" | "rejected" | "conflict">>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [activeConflict, setActiveConflict] = useState<{ candidate: MemoryCandidate; existingClaim: MemoryClaim } | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [outcomes, setOutcomes] = useState<Record<string, SimulateOutcomeResponse>>({});
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, resolved, decisions, outcomes]);

  function partnerName(partnerId: string): string {
    const node = graph?.nodes.find((n) => n.id === `creator:${partnerId}` || n.id === `publisher:${partnerId}`);
    return node?.label ?? partnerId.replace(/_/g, " ");
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setMessages((m) => [...m, { id: nextId(), role: "user", text: trimmed }]);
    setInput("");
    setSending(true);
    try {
      const resp = await api.sendChat(clientId, trimmed);
      if (resp.recommendation) {
        setMessages((m) => [...m, { id: nextId(), role: "recommendation", recommendation: resp.recommendation as RecommendationResponse }]);
        onHighlight(resp.recommendation.supporting_memory_ids);
      } else if (resp.candidates.length > 0) {
        setMessages((m) => [...m, { id: nextId(), role: "candidates", candidates: resp.candidates }]);
      } else {
        setMessages((m) => [...m, { id: nextId(), role: "assistant", text: resp.reply }]);
        if (resp.referenced_memory_ids.length > 0) onHighlight(resp.referenced_memory_ids);
      }
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  async function approve(c: MemoryCandidate) {
    setBusyId(c.id);
    try {
      const resp = await api.reviewMemory(c.id, "approve");
      if (resp.requires_conflict_resolution && resp.conflict_with_claim) {
        setResolved((r) => ({ ...r, [c.id]: "conflict" }));
        setActiveConflict({ candidate: c, existingClaim: resp.conflict_with_claim });
      } else {
        setResolved((r) => ({ ...r, [c.id]: "approved" }));
        onAfterMutation();
      }
    } finally {
      setBusyId(null);
    }
  }

  async function reject(c: MemoryCandidate) {
    setBusyId(c.id);
    try {
      await api.reviewMemory(c.id, "reject");
      setResolved((r) => ({ ...r, [c.id]: "rejected" }));
      onAfterMutation();
    } finally {
      setBusyId(null);
    }
  }

  async function approveAll(candidates: MemoryCandidate[]) {
    for (const c of candidates) {
      if (!resolved[c.id]) {
        // eslint-disable-next-line no-await-in-loop
        await approve(c);
      }
    }
  }

  async function resolveConflict(operation: "SUPERSEDE" | "REJECT") {
    if (!activeConflict) return;
    setBusyId(activeConflict.candidate.id);
    try {
      await api.resolveConflict(activeConflict.candidate.id, operation);
      setResolved((r) => ({ ...r, [activeConflict.candidate.id]: operation === "SUPERSEDE" ? "approved" : "rejected" }));
      setActiveConflict(null);
      onAfterMutation();
    } finally {
      setBusyId(null);
    }
  }

  async function acceptRecommendation(msgId: string, rec: RecommendationResponse) {
    setBusyId(msgId);
    try {
      const decision = await api.createDecision({
        client_id: rec.client_id,
        partner_id: rec.partner_id,
        summary: `Renew ${partnerName(rec.partner_id)} under ${rec.recommendation.replace(/_/g, " ")}`,
        terms: rec.recommended_terms,
        rationale: rec.explanation,
        motivated_by_claim_ids: rec.supporting_memory_ids,
      });
      setDecisions((d) => ({ ...d, [msgId]: decision }));
      onAfterMutation();
    } finally {
      setBusyId(null);
    }
  }

  async function simulateOutcome(msgId: string, decision: Decision) {
    setBusyId(msgId);
    try {
      const resp = await api.simulateOutcome(decision.id);
      setOutcomes((o) => ({ ...o, [msgId]: resp }));
      onAfterMutation();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-slate-200">
        <h2 className="text-sm font-semibold text-slate-800">Agent conversation</h2>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        {messages.length === 0 && (
          <div className="text-xs text-slate-400 space-y-2">
            <p>Try one of these, in order:</p>
            <div className="space-y-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="block text-left w-full rounded border border-dashed border-slate-300 px-2 py-1.5 hover:border-blue-400 hover:text-blue-700"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => {
          if (m.role === "user") {
            return (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[85%] rounded-lg bg-slate-800 text-white text-xs px-3 py-2">{m.text}</div>
              </div>
            );
          }
          if (m.role === "assistant") {
            return (
              <div key={m.id} className="flex justify-start">
                <div className="max-w-[90%] rounded-lg bg-white border border-slate-200 text-xs px-3 py-2 whitespace-pre-line text-slate-700">
                  {m.text}
                </div>
              </div>
            );
          }
          if (m.role === "candidates") {
            return (
              <CandidateMemoryReview
                key={m.id}
                candidates={m.candidates}
                resolved={resolved}
                busyId={busyId}
                onApprove={approve}
                onReject={reject}
                onApproveAll={() => approveAll(m.candidates)}
              />
            );
          }
          return (
            <RecommendationCard
              key={m.id}
              recommendation={m.recommendation}
              decision={decisions[m.id] ?? null}
              outcomeResp={outcomes[m.id] ?? null}
              busy={busyId === m.id}
              onAccept={() => acceptRecommendation(m.id, m.recommendation)}
              onSimulate={() => decisions[m.id] && simulateOutcome(m.id, decisions[m.id])}
            />
          );
        })}

        {sending && <div className="text-xs text-slate-400 italic">thinking…</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="border-t border-slate-200 p-2 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tell the agent something, or ask a question…"
          className="flex-1 text-xs rounded border border-slate-300 px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="text-xs px-3 py-1.5 rounded bg-slate-800 text-white hover:bg-slate-900 disabled:opacity-40"
        >
          Send
        </button>
      </form>

      {activeConflict && (
        <ConflictDialog
          candidate={activeConflict.candidate}
          existingClaim={activeConflict.existingClaim}
          busy={busyId === activeConflict.candidate.id}
          onResolve={resolveConflict}
          onDismiss={() => setActiveConflict(null)}
        />
      )}
    </div>
  );
}
