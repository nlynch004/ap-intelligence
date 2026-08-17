"use client";

import { ACCENT, FONT_MONO, TEXT, predicateLabel, sentenceCase } from "@/lib/design";
import type { DecisionEvidence } from "@/lib/types";

function fmtMoney(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtPct(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

function fmtRoas(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `${v.toFixed(2)}x`;
}

/**
 * Renders backend/app/schemas.py::DecisionEvidence, built deterministically
 * in app/memory/retrieval.py from actual retrieved DB rows - not parsed from
 * `evidence_brief` prose and not produced by the LLM. Five sub-blocks, in the
 * order the panel should be read: what's observed, what AP currently
 * believes, what's uncertain, what portfolio experience (clearly synthetic)
 * is informing the recommendation - rendered inside the single "Decision
 * Evidence" surface owned by RecommendationCard (design_handoff v2 Sec.3).
 */
export function DecisionEvidencePanel({ evidence }: { evidence: DecisionEvidence }) {
  const { commercial_ask, prior_performance, measurement_cautions, client_memory, portfolio_evidence } = evidence;

  return (
    <>
      {/* 1. Commercial ask */}
      {(commercial_ask.proposed_fee != null || commercial_ask.prior_fee != null) && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 6 }}>Commercial ask</div>
          <div style={{ fontSize: 16, color: TEXT.primary, fontWeight: 600 }}>{fmtMoney(commercial_ask.proposed_fee)} proposed</div>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginTop: 2 }}>
            {fmtMoney(commercial_ask.prior_fee)} prior fee
            {commercial_ask.increase_pct != null && <span style={{ color: ACCENT.amber }}> · {fmtPct(commercial_ask.increase_pct)}</span>}
          </div>
        </div>
      )}

      {/* 2. Historical performance */}
      {prior_performance.length > 0 && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 8 }}>Historical performance</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {prior_performance.map((c) => (
              <div key={c.campaign_id} style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 14, color: TEXT.strongSecondary2 }}>
                <span>{c.month_label}</span>
                <span style={{ color: TEXT.secondary }}>
                  {fmtMoney(c.fee)} → {fmtMoney(c.attributed_revenue)}
                </span>
                <span style={{ fontFamily: FONT_MONO, fontSize: 13, color: ACCENT.green }}>{fmtRoas(c.attributed_roas)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Governed context - dynamic list of active claims relevant to this decision (strategy, goals, relationship/negotiation history, tradeoffs), not a fixed set of rows. */}
      {client_memory.length > 0 && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 8 }}>Governed context</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14, lineHeight: 1.5 }}>
            {client_memory.map((m) => (
              <div key={m.claim_id}>
                <span style={{ color: TEXT.metadata }}>{predicateLabel(m.predicate)}</span>
                <br />
                <span style={{ color: TEXT.primary }}>{sentenceCase(m.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Measurement caution - the only tinted sub-surface in the card. Unverified hypotheses, given visual weight but framed as uncertainty, not alarm. */}
      {measurement_cautions.length > 0 && (
        <div style={{ background: "rgba(201,151,90,0.06)", borderRadius: 10, padding: 14, marginBottom: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ color: ACCENT.amber, fontSize: 12 }}>△</span>
            <span style={{ fontSize: 13, color: ACCENT.amber, fontWeight: 600 }}>Measurement caution</span>
          </div>
          {measurement_cautions.map((c, i) => (
            <div key={c.claim_id} style={{ marginBottom: i === measurement_cautions.length - 1 ? 0 : 14 }}>
              <div style={{ fontSize: 14, color: "#d5cbb8", fontWeight: 600, marginBottom: 6 }}>{sentenceCase(c.value)}</div>
              <div style={{ fontSize: 14, color: "#a89b85", lineHeight: 1.55 }}>{c.summary}</div>
              <div style={{ fontSize: 12, fontFamily: FONT_MONO, color: "#8a7e6b", marginTop: 8 }}>
                unverified hypothesis · confidence {c.confidence.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 5. Portfolio experience - synthetic, never presented as real client data */}
      {portfolio_evidence && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 6 }}>Portfolio experience</div>
          <div style={{ fontSize: 14, color: TEXT.primary }}>
            <span style={{ color: ACCENT.purple }}>
              {portfolio_evidence.evidence_count} comparable case{portfolio_evidence.evidence_count === 1 ? "" : "s"}
            </span>
            {portfolio_evidence.positive_outcomes != null ? ` (${portfolio_evidence.positive_outcomes} positive)` : ""}
            {portfolio_evidence.description ? ` · ${portfolio_evidence.description}` : ""}
          </div>
          {portfolio_evidence.synthetic && (
            <div style={{ fontSize: 11, letterSpacing: "0.08em", color: "#6b6288", marginTop: 6 }}>SYNTHETIC</div>
          )}
        </div>
      )}
    </>
  );
}
