"use client";

import { ACCENT, SURFACE, TEXT, sentenceCase } from "@/lib/design";
import type { Decision, RecommendationResponse, SimulateOutcomeResponse } from "@/lib/types";
import { DecisionEvidencePanel } from "./DecisionEvidencePanel";

const primaryButton: React.CSSProperties = {
  marginTop: 14,
  fontSize: 13,
  fontWeight: 600,
  color: "#0d1a17",
  background: ACCENT.green,
  border: "none",
  borderRadius: 8,
  padding: "9px 16px",
  cursor: "pointer",
};

export function RecommendationCard({
  recommendation,
  decision,
  outcomeResp,
  busy,
  onAccept,
  onSimulate,
}: {
  recommendation: RecommendationResponse;
  decision: Decision | null;
  outcomeResp: SimulateOutcomeResponse | null;
  busy: boolean;
  onAccept: () => void;
  onSimulate: () => void;
}) {
  const terms = recommendation.recommended_terms;
  const termsLine = `$${terms.base_fee.toLocaleString()} base + ${terms.performance_bonus_pct}% performance bonus`;
  const note = [recommendation.explanation, ...recommendation.uncertainties].filter(Boolean).join(" ");

  return (
    <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 18, animation: "fadeup 0.3s ease" }}>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 16 }}>DECISION EVIDENCE</div>

      {/* Evidence first: what does the system know, what's uncertain, what
       * prior experience is it using - then, below, what it recommended. */}
      <DecisionEvidencePanel evidence={recommendation.decision_evidence} />

      <div style={{ borderTop: `1px solid ${SURFACE.separatorInner2}`, paddingTop: 16 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 10 }}>RECOMMENDATION</div>
        <div style={{ fontSize: 18, fontWeight: 600, color: TEXT.primary }}>{sentenceCase(recommendation.recommendation)}</div>
        <div style={{ fontSize: 14, color: TEXT.secondary, marginTop: 4 }}>{termsLine}</div>
        {note && <div style={{ fontSize: 13.5, lineHeight: 1.6, color: TEXT.secondary2, marginTop: 10 }}>{note}</div>}

        {!decision && (
          <button disabled={busy} onClick={onAccept} style={{ ...primaryButton, opacity: busy ? 0.6 : 1 }}>
            Accept recommendation
          </button>
        )}

        {decision && (
          <div style={{ marginTop: 14, fontSize: 13, color: ACCENT.green }}>
            ✓ Decision captured: <span style={{ fontWeight: 600 }}>{decision.summary}</span>
          </div>
        )}

        {decision && !outcomeResp && (
          <button disabled={busy} onClick={onSimulate} style={{ ...primaryButton, marginTop: 10 }}>
            Simulate outcome
          </button>
        )}

        {outcomeResp && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: TEXT.strongSecondary2, marginBottom: 6 }}>
              Simulated outcome: {sentenceCase(outcomeResp.outcome.outcome_label)}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {Object.entries(outcomeResp.outcome.metrics).map(([k, val]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: TEXT.secondary }}>
                  <span>{k.replace(/_/g, " ")}</span>
                  <span style={{ color: TEXT.strongSecondary2, fontWeight: 500 }}>{String(val)}</span>
                </div>
              ))}
            </div>
            {outcomeResp.pattern_id && (
              <div style={{ marginTop: 8, fontSize: 13, color: ACCENT.purple }}>
                Portfolio evidence: {outcomeResp.pattern_evidence_count_before} → {outcomeResp.pattern_evidence_count_after}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
