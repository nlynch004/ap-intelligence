"use client";

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
    <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-3 mt-2">
      <div className="text-xs font-medium text-blue-900 mb-2">
        I found {candidates.length} potentially useful {candidates.length === 1 ? "memory" : "memories"}.
      </div>
      <ul className="space-y-1.5">
        {candidates.map((c) => {
          const isHypothesis = c.claim_payload.claim_class === "hypothesis";
          const state = resolved[c.id];
          return (
            <li key={c.id} className="flex items-start justify-between gap-2 text-xs bg-white rounded border border-slate-200 px-2 py-1.5">
              <div className="min-w-0">
                <div className="flex items-center gap-1">
                  <span>{isHypothesis ? "⚠️" : state === "conflict" ? "🔁" : "✓"}</span>
                  <span className="font-medium text-slate-800 truncate">
                    {c.claim_payload.subject_label} {c.claim_payload.predicate.replace(/_/g, " ")}: {c.claim_payload.value.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {CLASS_LABEL[c.claim_payload.claim_class] ?? c.claim_payload.claim_class} · confidence {c.claim_payload.confidence.toFixed(2)}
                  {c.proposed_operation === "SUPERSEDE" && " · conflicts with an active belief"}
                </div>
              </div>
              <div className="shrink-0 flex gap-1">
                {state ? (
                  <span
                    className={
                      "text-[10px] px-1.5 py-0.5 rounded-full font-medium " +
                      (state === "approved"
                        ? "bg-emerald-100 text-emerald-700"
                        : state === "conflict"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-slate-100 text-slate-500")
                    }
                  >
                    {state === "conflict" ? "needs resolution" : state}
                  </span>
                ) : (
                  <>
                    <button
                      disabled={busyId === c.id}
                      onClick={() => onApprove(c)}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      disabled={busyId === c.id}
                      onClick={() => onReject(c)}
                      className="text-[10px] px-1.5 py-0.5 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      {!allDone && (
        <button
          onClick={onApproveAll}
          className="mt-2 text-[11px] px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          Approve all
        </button>
      )}
    </div>
  );
}
