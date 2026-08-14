"use client";

import type { MemoryCandidate, MemoryClaim } from "@/lib/types";

export function ConflictDialog({
  candidate,
  existingClaim,
  busy,
  onResolve,
  onDismiss,
}: {
  candidate: MemoryCandidate;
  existingClaim: MemoryClaim;
  busy: boolean;
  onResolve: (operation: "SUPERSEDE" | "REJECT") => void;
  onDismiss: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-5">
        <div className="text-sm font-semibold text-slate-900 mb-1">Conflicting belief detected</div>
        <p className="text-xs text-slate-500 mb-4">
          This new statement contradicts an existing active memory. The system can change its mind without
          forgetting its history - approving will mark the old belief as historical and activate the new one.
        </p>

        <div className="space-y-2 mb-4">
          <div className="rounded border border-slate-200 bg-slate-50 p-2">
            <div className="text-[10px] uppercase tracking-wide text-slate-400 mb-0.5">Current (active)</div>
            <div className="text-xs text-slate-700">
              {existingClaim.predicate.replace(/_/g, " ")}: <span className="font-medium">{existingClaim.value.replace(/_/g, " ")}</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">valid since {existingClaim.valid_from}</div>
          </div>
          <div className="text-center text-slate-400 text-xs">↓ SUPERSEDE ↓</div>
          <div className="rounded border border-blue-200 bg-blue-50 p-2">
            <div className="text-[10px] uppercase tracking-wide text-blue-400 mb-0.5">Proposed (new)</div>
            <div className="text-xs text-blue-800">
              {candidate.claim_payload.predicate.replace(/_/g, " ")}:{" "}
              <span className="font-medium">{candidate.claim_payload.value.replace(/_/g, " ")}</span>
            </div>
            <div className="text-[10px] text-blue-400 mt-0.5">confidence {candidate.claim_payload.confidence.toFixed(2)}</div>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <button
            disabled={busy}
            onClick={onDismiss}
            className="text-xs px-3 py-1.5 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            Decide later
          </button>
          <button
            disabled={busy}
            onClick={() => onResolve("REJECT")}
            className="text-xs px-3 py-1.5 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            Keep old belief
          </button>
          <button
            disabled={busy}
            onClick={() => onResolve("SUPERSEDE")}
            className="text-xs px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Supersede
          </button>
        </div>
      </div>
    </div>
  );
}
