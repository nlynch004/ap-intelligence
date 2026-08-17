"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { ACCENT, FONT_MONO, SURFACE, TEXT } from "@/lib/design";
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

// The three-step "Creator renewal" workflow (design_handoff v2 Sec.2) maps
// 1:1 to this demo script's canned prompts - the same prompts previously
// offered as free-standing suggestion buttons. `stage` below is derived from
// real conversation/candidate/recommendation state, never persisted
// separately (spec "State Management": workflow state must remain a
// projection of real application state).
const STEP_DEFS = [
  { title: "Account context", desc: "Retrieve current Northwind context", prompt: "Bring me up to speed on Northwind." },
  {
    title: "Strategy update",
    desc: "Capture what changed",
    prompt:
      "Northwind's strategy changed after last week's executive review. They now want to reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS is a little lower.",
  },
  { title: "Renewal decision", desc: "Evaluate Summit Sisters", prompt: "Summit Sisters wants $6,000 for another campaign. Should we renew them?" },
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
  /** focusIds, when given, are the graph node ids of whatever was just
   * created/changed - the parent re-frames the graph viewport around them. */
  onAfterMutation: (focusIds?: string[]) => void;
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

  // Derived workflow stage (0-3): how many of the three canned steps have
  // run their course. Never a separate source of truth - just a read of the
  // conversation transcript that's already state here.
  const stage = useMemo(() => {
    const hasAssistantReply = messages.some((m) => m.role === "assistant");
    const candidateMsgs = messages.filter((m): m is Extract<Msg, { role: "candidates" }> => m.role === "candidates");
    const hasCandidates = candidateMsgs.length > 0;
    const hasRecommendation = messages.some((m) => m.role === "recommendation");
    const candidatesAllResolved = hasCandidates && candidateMsgs.every((m) => m.candidates.every((c) => resolved[c.id] === "approved" || resolved[c.id] === "rejected"));

    let s = 0;
    if (hasAssistantReply || hasCandidates || hasRecommendation) s = 1;
    if (candidatesAllResolved) s = Math.max(s, 2);
    if (hasRecommendation) s = 3;
    return s;
  }, [messages, resolved]);

  function partnerName(partnerId: string): string {
    // Graph node ids are keyed by the backend's raw entity-table name
    // ("partner"), not the resolved display kind ("creator"/"publisher") -
    // see node_key() in app/routers/graph.py.
    const node = graph?.nodes.find((n) => n.id === `partner:${partnerId}`);
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
        onAfterMutation(resp.claim ? [`memory_claim:${resp.claim.id}`] : undefined);
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
        await approve(c);
      }
    }
  }

  async function resolveConflict(operation: "SUPERSEDE" | "REJECT") {
    if (!activeConflict) return;
    setBusyId(activeConflict.candidate.id);
    try {
      const resp = await api.resolveConflict(activeConflict.candidate.id, operation);
      setResolved((r) => ({ ...r, [activeConflict.candidate.id]: operation === "SUPERSEDE" ? "approved" : "rejected" }));
      setActiveConflict(null);
      // Focus both the new active claim and the now-superseded one, so the
      // supersession is visually legible (old node dimmed, new one active).
      const focusIds = [resp.new_claim, resp.superseded_claim]
        .filter((c): c is NonNullable<typeof c> => c != null)
        .map((c) => `memory_claim:${c.id}`);
      onAfterMutation(focusIds.length > 0 ? focusIds : undefined);
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
      onAfterMutation([`decision:${decision.id}`]);
    } finally {
      setBusyId(null);
    }
  }

  async function simulateOutcome(msgId: string, decision: Decision) {
    setBusyId(msgId);
    try {
      const resp = await api.simulateOutcome(decision.id);
      setOutcomes((o) => ({ ...o, [msgId]: resp }));
      const focusIds = [`outcome:${resp.outcome.id}`];
      if (resp.pattern_id) focusIds.push(`portfolio_pattern:${resp.pattern_id}`);
      onAfterMutation(focusIds);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "22px 22px 16px" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 14 }}>CREATOR RENEWAL</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {STEP_DEFS.map((step, i) => {
            const done = stage > i;
            const current = stage === i;
            const clickable = i <= stage && !sending;
            const statusText = done ? "✓ Complete" : current ? "● Current" : "○ Next";
            const statusColor = done ? ACCENT.green : current ? ACCENT.blue : TEXT.faint2;
            const titleColor = current ? TEXT.primary : done ? TEXT.strongSecondary2 : TEXT.secondary2;
            return (
              <button
                key={step.title}
                onClick={() => clickable && send(step.prompt)}
                disabled={!clickable}
                style={{
                  display: "flex",
                  gap: 14,
                  textAlign: "left",
                  background: current ? SURFACE.activeRow : "transparent",
                  border: "none",
                  borderRadius: 8,
                  padding: "11px 12px",
                  cursor: clickable ? "pointer" : "default",
                  width: "100%",
                }}
              >
                <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: TEXT.faint2, paddingTop: 2, flex: "none" }}>{String(i + 1).padStart(2, "0")}</span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ display: "block", fontSize: 14, fontWeight: 600, color: titleColor }}>{step.title}</span>
                  <span style={{ display: "block", fontSize: 13, color: TEXT.metadata, marginTop: 1 }}>{step.desc}</span>
                </span>
                <span style={{ fontSize: 12, color: statusColor, flex: "none", paddingTop: 3, whiteSpace: "nowrap" }}>{statusText}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ padding: "6px 22px 10px", borderTop: `1px solid ${SURFACE.separatorInner}` }}>
        <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, paddingTop: 14 }}>CONVERSATION</div>
      </div>

      <div ref={scrollRef} className="ap-scroll" style={{ flex: 1, overflowY: "auto", padding: "6px 22px 22px", display: "flex", flexDirection: "column", gap: 14, minHeight: 0 }}>
        {messages.length === 0 && <div style={{ fontSize: 13, color: TEXT.faint, fontStyle: "italic" }}>Use the steps above, or ask a question below.</div>}

        {messages.map((m) => {
          if (m.role === "user") {
            return (
              <div key={m.id} style={{ display: "flex", justifyContent: "flex-end" }}>
                <div style={{ maxWidth: "88%", borderRadius: 12, padding: "10px 14px", fontSize: 14, lineHeight: 1.55, whiteSpace: "pre-line", background: "#18222f", color: TEXT.primary, animation: "fadeup 0.25s ease" }}>
                  {m.text}
                </div>
              </div>
            );
          }
          if (m.role === "assistant") {
            return (
              <div key={m.id} style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{ maxWidth: "100%", fontSize: 14, lineHeight: 1.55, whiteSpace: "pre-line", color: "#b3c0d3", animation: "fadeup 0.25s ease" }}>{m.text}</div>
              </div>
            );
          }
          if (m.role === "candidates") {
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <CandidateMemoryReview
                  candidates={m.candidates}
                  resolved={resolved}
                  busyId={busyId}
                  onApprove={approve}
                  onReject={reject}
                  onApproveAll={() => approveAll(m.candidates)}
                />
              </div>
            );
          }
          return (
            <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
              <RecommendationCard
                recommendation={m.recommendation}
                decision={decisions[m.id] ?? null}
                outcomeResp={outcomes[m.id] ?? null}
                busy={busyId === m.id}
                onAccept={() => acceptRecommendation(m.id, m.recommendation)}
                onSimulate={() => decisions[m.id] && simulateOutcome(m.id, decisions[m.id])}
              />
            </div>
          );
        })}

        {sending && <div style={{ fontSize: 13, color: TEXT.faint, fontStyle: "italic" }}>thinking…</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        style={{ borderTop: `1px solid ${SURFACE.separatorInner}`, padding: 12, display: "flex", gap: 8 }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tell the agent something, or ask a question…"
          style={{ flex: 1, fontSize: 13, borderRadius: 8, border: `1px solid ${SURFACE.separator}`, background: SURFACE.raised, color: TEXT.primary, padding: "9px 12px", outline: "none" }}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          style={{ fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8, border: "none", background: "#18222f", color: TEXT.primary, cursor: "pointer", opacity: sending || !input.trim() ? 0.4 : 1 }}
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
