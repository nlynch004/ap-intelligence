"use client";

import { ACCENT, SURFACE, TEXT } from "@/lib/design";
import type { MemoryCandidate } from "@/lib/types";

const CLASS_LABEL: Record<string, string> = {
  verified_fact: "verified fact",
  account_preference: "account preference",
  historical_observation: "historical observation",
  hypothesis: "hypothesis",
};

export function CandidateMemoryReview({
  candidates,
  resolved,
  busyId,
  onApprove,
  onReject,
  onApproveAll,
}: {
  candidates: MemoryCandidate[];
  resolved: Record<string, "approved" | "rejected" | "conflict">;
  busyId: string | null;
  onApprove: (c: MemoryCandidate) => void;
  onReject: (c: MemoryCandidate) => void;
  onApproveAll: () => void;
}) {
  const allDone = candidates.every((c) => resolved[c.id]);

  return (
    <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 16 }}>
      <div style={{ fontSize: 13, color: TEXT.strongSecondary2, marginBottom: 10 }}>
        I found {candidates.length} potentially useful {candidates.length === 1 ? "memory" : "memories"}.
      </div>
      <ul style={{ display: "flex", flexDirection: "column", gap: 8, listStyle: "none", padding: 0, margin: 0 }}>
        {candidates.map((c) => {
          const isHypothesis = c.claim_payload.claim_class === "hypothesis";
          const state = resolved[c.id];
          const accent = isHypothesis ? ACCENT.amber : ACCENT.blue;
          return (
            <li key={c.id} style={{ background: SURFACE.activeRow, borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ color: accent, fontSize: 12 }}>{isHypothesis ? "△" : state === "conflict" ? "↻" : "●"}</span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: TEXT.primary }}>
                      {c.claim_payload.subject_label} {c.claim_payload.predicate.replace(/_/g, " ")}: {c.claim_payload.value.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: TEXT.metadata, marginTop: 3 }}>
                    {CLASS_LABEL[c.claim_payload.claim_class] ?? c.claim_payload.claim_class} · confidence {c.claim_payload.confidence.toFixed(2)}
                    {c.proposed_operation === "SUPERSEDE" && " · conflicts with an active belief"}
                    {c.proposed_operation === "REQUEST_HUMAN_REVIEW" && " · unrecognized predicate, needs review"}
                  </div>
                  <div style={{ fontSize: 11, color: TEXT.faint, marginTop: 2 }}>
                    Source: {c.claim_payload.source_type.replace(/_/g, " ")}
                    {c.claim_payload.rationale && ` — ${c.claim_payload.rationale}`}
                  </div>
                </div>
                <div style={{ flex: "none", display: "flex", gap: 6 }}>
                  {state ? (
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: state === "approved" ? ACCENT.green : state === "conflict" ? ACCENT.amber : TEXT.faint,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {state === "conflict" ? "needs resolution" : state}
                    </span>
                  ) : (
                    <>
                      <button
                        disabled={busyId === c.id}
                        onClick={() => onApprove(c)}
                        style={{ fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 6, border: "none", background: ACCENT.blue, color: "#0a1622", cursor: "pointer", opacity: busyId === c.id ? 0.5 : 1 }}
                      >
                        Approve
                      </button>
                      <button
                        disabled={busyId === c.id}
                        onClick={() => onReject(c)}
                        style={{ fontSize: 11, padding: "4px 10px", borderRadius: 6, border: `1px solid ${SURFACE.separator}`, background: "transparent", color: TEXT.secondary, cursor: "pointer", opacity: busyId === c.id ? 0.5 : 1 }}
                      >
                        Reject
                      </button>
                    </>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      {!allDone && (
        <button
          onClick={onApproveAll}
          style={{ marginTop: 10, fontSize: 12, fontWeight: 600, padding: "7px 14px", borderRadius: 8, border: "none", background: ACCENT.blue, color: "#0a1622", cursor: "pointer" }}
        >
          Approve all
        </button>
      )}
    </div>
  );
}
