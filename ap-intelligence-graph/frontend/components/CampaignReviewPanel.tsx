"use client";

import { ACCENT, FONT_MONO, TEXT, predicateLabel, sentenceCase } from "@/lib/design";
import type { CampaignReviewEvidence } from "@/lib/types";

function fmtMoney(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtRoas(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `${v.toFixed(2)}x`;
}

function fmtDeltaPct(v: number | null): string {
  if (v === null || v === undefined) return "";
  return ` (${v >= 0 ? "+" : ""}${v.toFixed(1)}%)`;
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 8 }}>{label}</div>
      {children}
    </div>
  );
}

function Bullets({ items, color }: { items: string[]; color?: string }) {
  if (items.length === 0) return <div style={{ fontSize: 13.5, color: TEXT.faint, fontStyle: "italic" }}>None noted.</div>;
  return (
    <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
      {items.map((s, i) => (
        <li key={i} style={{ fontSize: 14, lineHeight: 1.55, color: color ?? TEXT.secondary2 }}>
          {s}
        </li>
      ))}
    </ul>
  );
}

/**
 * Renders backend/app/schemas.py::CampaignReviewEvidence (deterministic,
 * app/memory/retrieval.py::build_campaign_review_context) plus the bounded
 * review agent's own prose (summary/what_worked/what_is_uncertain/
 * planning_implications) - never the other way around. Candidate lessons
 * are rendered separately by ChatPanel via the existing CandidateMemoryReview
 * component (spec Phase 2: reuse the existing review UX, not a second
 * approval system), so this panel stops after PLANNING IMPLICATIONS.
 */
export function CampaignReviewPanel({
  evidence,
  summary,
  whatWorked,
  whatIsUncertain,
  planningImplications,
}: {
  evidence: CampaignReviewEvidence;
  summary: string;
  whatWorked: string[];
  whatIsUncertain: string[];
  planningImplications: string[];
}) {
  const comparison = evidence.prior_campaign_comparison;
  const governed = [...evidence.client_memory, ...evidence.partner_memory];

  return (
    <>
      <div style={{ fontSize: 15, fontWeight: 600, color: TEXT.primary, lineHeight: 1.4, marginBottom: 16 }}>{summary}</div>

      <Block label="OBSERVED PERFORMANCE">
        <div style={{ fontSize: 16, color: TEXT.primary, fontWeight: 600 }}>
          {fmtMoney(evidence.fee)} fee → {fmtMoney(evidence.attributed_revenue)} attributed
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 4 }}>
          <span style={{ fontFamily: FONT_MONO, fontSize: 14, color: ACCENT.green }}>{fmtRoas(evidence.attributed_roas)} ROAS</span>
          <span style={{ fontSize: 13, color: TEXT.metadata }}>
            {evidence.link_clicks?.toLocaleString() ?? "—"} clicks · {evidence.code_redemptions?.toLocaleString() ?? "—"} redemptions
          </span>
        </div>
        {comparison.has_prior && (
          <div style={{ fontSize: 13, color: TEXT.metadata, marginTop: 6 }}>
            vs. {comparison.prior_month_label}: revenue {comparison.revenue_delta != null ? fmtMoney(comparison.revenue_delta) : "—"}
            {fmtDeltaPct(comparison.revenue_delta_pct)}
            {comparison.roas_delta != null && <>, ROAS {comparison.roas_delta >= 0 ? "+" : ""}{comparison.roas_delta.toFixed(2)}x</>}
          </div>
        )}
        {evidence.synthetic && <div style={{ fontSize: 11, letterSpacing: "0.08em", color: "#6b6288", marginTop: 8 }}>SYNTHETIC</div>}
      </Block>

      {governed.length > 0 && (
        <Block label="RELEVANT GOVERNED CONTEXT">
          <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14, lineHeight: 1.5 }}>
            {governed.map((m) => (
              <div key={m.claim_id}>
                <span style={{ color: TEXT.metadata }}>{predicateLabel(m.predicate)}</span>
                <br />
                <span style={{ color: TEXT.primary }}>{sentenceCase(m.value)}</span>
              </div>
            ))}
          </div>
        </Block>
      )}

      <Block label="MEASUREMENT CONFIDENCE">
        {evidence.measurement_cautions.length === 0 ? (
          <div style={{ fontSize: 13.5, color: TEXT.secondary2 }}>No open measurement caution on file for this campaign.</div>
        ) : (
          <div style={{ background: "rgba(201,151,90,0.06)", borderRadius: 10, padding: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ color: ACCENT.amber, fontSize: 12 }}>△</span>
              <span style={{ fontSize: 13, color: ACCENT.amber, fontWeight: 600 }}>Unverified hypothesis</span>
            </div>
            {evidence.measurement_cautions.map((c, i) => (
              <div key={c.claim_id} style={{ marginBottom: i === evidence.measurement_cautions.length - 1 ? 0 : 14 }}>
                <div style={{ fontSize: 14, color: "#d5cbb8", fontWeight: 600, marginBottom: 6 }}>{sentenceCase(c.value)}</div>
                <div style={{ fontSize: 14, color: "#a89b85", lineHeight: 1.55 }}>{c.summary}</div>
                <div style={{ fontSize: 12, fontFamily: FONT_MONO, color: "#8a7e6b", marginTop: 8 }}>
                  {c.status.replace(/_/g, " ")} · confidence {c.confidence.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Block>

      <Block label="WHAT WORKED">
        <Bullets items={whatWorked} />
      </Block>

      <Block label="WHAT REMAINS UNCERTAIN">
        <Bullets items={whatIsUncertain} color={ACCENT.amber} />
      </Block>

      <Block label="PLANNING IMPLICATIONS">
        <Bullets items={planningImplications} />
      </Block>
    </>
  );
}
