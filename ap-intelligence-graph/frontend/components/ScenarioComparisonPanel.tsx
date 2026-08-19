"use client";

import { ACCENT, FONT_MONO, SURFACE, TEXT } from "@/lib/design";
import type { ScenarioComparisonEvidence, ScenarioWithAssessment } from "@/lib/types";

function fmtMoney(v: number): string {
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtRoas(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `${v.toFixed(2)}x`;
}

const GOOD = ACCENT.green;
const OK = ACCENT.amber;
const BAD = "#c9707a"; // muted rose/red, distinct from the amber caution tone used elsewhere
const NEUTRAL = TEXT.faint;

// "high"/"low" mean opposite things depending on the dimension - high
// relationship_continuity is good, but high measurement_exposure is bad.
// Keying the color purely off the string value (as an earlier version of
// this component did) colored both the same green, which is backwards for
// exposure. Each dimension gets its own explicit value->color mapping
// instead of one shared table.
const RATING_COLORS: Record<string, Record<string, string>> = {
  strategy_alignment: { strong: GOOD, moderate: OK, weak: BAD, unknown: NEUTRAL },
  measurement_alignment: { strong: GOOD, moderate: OK, weak: BAD, unknown: NEUTRAL },
  measurement_exposure: { low: GOOD, moderate: OK, high: BAD, unknown: NEUTRAL },
  relationship_continuity: { high: GOOD, moderate: OK, low: BAD, unknown: NEUTRAL },
};

function Rating({ dimension, label, value }: { dimension: keyof typeof RATING_COLORS | "structure"; label: string; value: string }) {
  const color = dimension === "structure" ? TEXT.secondary2 : (RATING_COLORS[dimension]?.[value] ?? TEXT.secondary2);
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontSize: 13 }}>
      <span style={{ color: TEXT.metadata }}>{label}</span>
      <span style={{ color, fontWeight: 600, textTransform: "capitalize" }}>{value.replace(/_/g, " ")}</span>
    </div>
  );
}

function ScenarioCard({ item, isPreferred }: { item: ScenarioWithAssessment; isPreferred: boolean }) {
  const { scenario: s, assessment: a } = item;
  return (
    <div
      style={{
        flex: "1 1 220px", minWidth: 200, background: isPreferred ? "rgba(79,185,141,0.06)" : SURFACE.nodeResting,
        border: `1px solid ${isPreferred ? "rgba(79,185,141,0.3)" : SURFACE.nodeBorderResting}`,
        borderRadius: 10, padding: 16,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div style={{ fontSize: 14.5, fontWeight: 600, color: TEXT.primary }}>{s.label}</div>
        {isPreferred && <span style={{ fontSize: 10, letterSpacing: "0.06em", color: ACCENT.green, fontFamily: FONT_MONO, flex: "none" }}>PREFERRED</span>}
      </div>
      <div style={{ fontSize: 20, fontWeight: 600, color: TEXT.primary, marginBottom: 2 }}>{fmtMoney(a.guaranteed_spend)}</div>
      <div style={{ fontSize: 12, color: TEXT.faint, marginBottom: 12 }}>
        guaranteed spend
        {a.change_vs_latest_fee_pct != null && (
          <span style={{ color: a.change_vs_latest_fee_pct > 0 ? ACCENT.amber : TEXT.faint }}>
            {" "}· {a.change_vs_latest_fee_pct >= 0 ? "+" : ""}{a.change_vs_latest_fee_pct.toFixed(1)}% vs latest fee
          </span>
        )}
      </div>
      {s.performance_bonus_pct > 0 && (
        <div style={{ fontSize: 12, color: TEXT.metadata, marginBottom: 12 }}>
          + {s.performance_bonus_pct}% bonus on {s.bonus_basis?.replace(/_/g, " ")}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 6, borderTop: `1px solid ${SURFACE.separatorInner2}`, paddingTop: 10 }}>
        <Rating dimension="structure" label="Structure" value={a.compensation_structure} />
        <Rating dimension="strategy_alignment" label="Strategy alignment" value={a.strategy_alignment} />
        <Rating dimension="measurement_alignment" label="Measurement alignment" value={a.measurement_alignment} />
        <Rating dimension="measurement_exposure" label="Measurement exposure" value={a.measurement_exposure} />
        <Rating dimension="relationship_continuity" label="Relationship continuity" value={a.relationship_continuity} />
      </div>
    </div>
  );
}

/**
 * Renders backend/app/schemas.py::ScenarioComparisonEvidence (deterministic,
 * app/memory/scenario_rules.py + retrieval.py::build_scenario_comparison_context)
 * plus the bounded comparison agent's own prose. The three scenario cards
 * are tagged APPLICATION ASSESSMENT; the summary/tradeoffs/uncertainties/
 * questions below are tagged MODEL SYNTHESIS - kept visually distinct per
 * spec Phase 5 Sec.13 ("That separation is essential").
 */
export function ScenarioComparisonPanel({
  evidence,
  preferredScenarioId,
  comparisonSummary,
  tradeoffs,
  uncertainties,
  questionsBeforeFinalizing,
  confidence,
  onHighlight,
  onUseInPlan,
  usedInPlan,
}: {
  evidence: ScenarioComparisonEvidence;
  preferredScenarioId: string;
  comparisonSummary: string;
  tradeoffs: string[];
  uncertainties: string[];
  questionsBeforeFinalizing: string[];
  confidence: number;
  onHighlight?: (ids: string[]) => void;
  /** Phase 6 Sec.16: carries this already-generated comparison into the
   * planning draft (frontend-only state) - does NOT persist a
   * PlannedAction. The model-preferred scenario becomes a planning
   * recommendation, not an approved decision (spec Sec.35). */
  onUseInPlan?: () => void;
  usedInPlan?: boolean;
}) {
  const stats = evidence.performance_stats;

  return (
    <>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 4 }}>SCENARIO COMPARISON</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: TEXT.primary, marginBottom: 12 }}>{evidence.partner.name}</div>

      <div style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
          <div style={{ fontSize: 12.5, color: TEXT.metadata }}>Current planning context</div>
          <span style={{ fontSize: 10, letterSpacing: "0.06em", color: ACCENT.teal, fontFamily: FONT_MONO }}>STRUCTURED SOURCE DATA</span>
        </div>
        <div
          onClick={onHighlight ? () => onHighlight(evidence.campaigns.map((c) => `campaign:${c.campaign_id}`)) : undefined}
          style={{ fontSize: 13, color: TEXT.secondary2, cursor: onHighlight ? "pointer" : "default" }}
        >
          {stats.campaign_count} campaign{stats.campaign_count === 1 ? "" : "s"} on file · latest {fmtRoas(stats.most_recent_roas)} ROAS · avg {fmtRoas(stats.average_roas)}
          {evidence.measurement_cautions.length > 0 ? " · open measurement caution" : " · no open measurement caution"}
          {evidence.partner.synthetic && " · SYNTHETIC"}
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
        <span style={{ fontSize: 10, letterSpacing: "0.06em", color: ACCENT.teal, fontFamily: FONT_MONO }}>APPLICATION ASSESSMENT</span>
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
        {evidence.scenarios.map((item) => (
          <ScenarioCard key={item.scenario.id} item={item} isPreferred={item.scenario.id === preferredScenarioId} />
        ))}
      </div>

      <div style={{ borderTop: `1px solid ${SURFACE.separatorInner2}`, paddingTop: 16 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 10 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint }}>AGENT ASSESSMENT</div>
          <span style={{ fontSize: 10.5, letterSpacing: "0.06em", color: ACCENT.purple, fontFamily: FONT_MONO }}>MODEL SYNTHESIS</span>
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.55, color: TEXT.primary, marginBottom: 12 }}>{comparisonSummary}</div>

        {tradeoffs.length > 0 && (
          <ul style={{ margin: "0 0 14px", paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
            {tradeoffs.map((t, i) => (
              <li key={i} style={{ fontSize: 13.5, lineHeight: 1.5, color: TEXT.secondary2 }}>{t}</li>
            ))}
          </ul>
        )}

        {uncertainties.length > 0 && (
          <>
            <div style={{ fontSize: 12.5, color: ACCENT.amber, marginBottom: 6 }}>Uncertainties</div>
            <ul style={{ margin: "0 0 14px", paddingLeft: 18, display: "flex", flexDirection: "column", gap: 5 }}>
              {uncertainties.map((u, i) => (
                <li key={i} style={{ fontSize: 13.5, lineHeight: 1.5, color: "#d2a468" }}>{u}</li>
              ))}
            </ul>
          </>
        )}

        {questionsBeforeFinalizing.length > 0 && (
          <>
            <div style={{ fontSize: 12.5, color: ACCENT.blue, marginBottom: 6 }}>Questions before finalizing</div>
            <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 5 }}>
              {questionsBeforeFinalizing.map((q, i) => (
                <li key={i} style={{ fontSize: 13.5, lineHeight: 1.5, color: TEXT.secondary2 }}>{q}</li>
              ))}
            </ul>
          </>
        )}

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 14 }}>
          <div style={{ fontSize: 11.5, color: TEXT.faint, fontFamily: FONT_MONO }}>confidence {confidence.toFixed(2)}</div>
          {onUseInPlan && (
            <button
              onClick={onUseInPlan}
              disabled={usedInPlan}
              style={{
                fontSize: 12.5, fontWeight: 600, padding: "7px 14px", borderRadius: 8,
                border: `1px solid ${usedInPlan ? SURFACE.separatorInner2 : ACCENT.blue}`,
                background: "transparent", color: usedInPlan ? TEXT.faint : ACCENT.blue,
                cursor: usedInPlan ? "default" : "pointer",
              }}
            >
              {usedInPlan ? "✓ Added to plan draft" : "Use in plan"}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
