"use client";

import { ACCENT, SURFACE, TEXT } from "@/lib/design";
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
    <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(4,6,10,0.6)", padding: 16 }}>
      <div style={{ background: SURFACE.raised, borderRadius: 12, boxShadow: "0 8px 24px rgba(0,0,0,0.5)", maxWidth: 420, width: "100%", padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: TEXT.primary, marginBottom: 6 }}>Conflicting belief detected</div>
        <p style={{ fontSize: 13, color: TEXT.secondary2, marginBottom: 16, lineHeight: 1.5 }}>
          This new statement contradicts an existing active memory. The system can change its mind without forgetting its history - approving will mark
          the old belief as historical and activate the new one.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
          <div style={{ background: SURFACE.nodeResting, border: `1px solid ${SURFACE.nodeBorderResting}`, borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 11, letterSpacing: "0.06em", color: TEXT.faint, marginBottom: 3 }}>CURRENT (ACTIVE)</div>
            <div style={{ fontSize: 13, color: TEXT.strongSecondary2 }}>
              {existingClaim.predicate.replace(/_/g, " ")}: <span style={{ fontWeight: 600, color: TEXT.primary }}>{existingClaim.value.replace(/_/g, " ")}</span>
            </div>
            <div style={{ fontSize: 11, color: TEXT.faint, marginTop: 3 }}>valid since {existingClaim.valid_from}</div>
          </div>
          <div style={{ textAlign: "center", color: TEXT.faint, fontSize: 12 }}>↓ supersede ↓</div>
          <div style={{ background: "#0e1620", border: "1px solid #1c2b3a", borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "#5b9fd4", marginBottom: 3 }}>PROPOSED (NEW)</div>
            <div style={{ fontSize: 13, color: "#8fbfe3" }}>
              {candidate.claim_payload.predicate.replace(/_/g, " ")}:{" "}
              <span style={{ fontWeight: 600, color: TEXT.primary }}>{candidate.claim_payload.value.replace(/_/g, " ")}</span>
            </div>
            <div style={{ fontSize: 11, color: "#5b9fd4", marginTop: 3 }}>confidence {candidate.claim_payload.confidence.toFixed(2)}</div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button
            disabled={busy}
            onClick={onDismiss}
            style={{ fontSize: 13, padding: "7px 14px", borderRadius: 8, border: `1px solid ${SURFACE.separator}`, background: "transparent", color: TEXT.secondary, cursor: "pointer", opacity: busy ? 0.5 : 1 }}
          >
            Decide later
          </button>
          <button
            disabled={busy}
            onClick={() => onResolve("REJECT")}
            style={{ fontSize: 13, padding: "7px 14px", borderRadius: 8, border: `1px solid ${SURFACE.separator}`, background: "transparent", color: TEXT.secondary, cursor: "pointer", opacity: busy ? 0.5 : 1 }}
          >
            Keep old belief
          </button>
          <button
            disabled={busy}
            onClick={() => onResolve("SUPERSEDE")}
            style={{ fontSize: 13, fontWeight: 600, padding: "7px 14px", borderRadius: 8, border: "none", background: ACCENT.blue, color: "#0a1622", cursor: "pointer", opacity: busy ? 0.5 : 1 }}
          >
            Supersede
          </button>
        </div>
      </div>
    </div>
  );
}
