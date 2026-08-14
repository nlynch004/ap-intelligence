"use client";

import type { Decision, RecommendationResponse, SimulateOutcomeResponse } from "@/lib/types";

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

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3 mt-2">
      <div className="text-xs font-semibold text-emerald-900 mb-1">
        RECOMMENDATION: {recommendation.recommendation.replace(/_/g, " ")}
      </div>
      <div className="rounded bg-white border border-emerald-200 p-2 text-xs mb-2">
        <div className="flex justify-between"><span className="text-slate-500">Base fee</span><span className="font-medium">${terms.base_fee.toLocaleString()}</span></div>
        <div className="flex justify-between"><span className="text-slate-500">Performance bonus</span><span className="font-medium">{terms.performance_bonus_pct}%</span></div>
        <div className="flex justify-between"><span className="text-slate-500">Bonus basis</span><span className="font-medium">{String(terms.bonus_basis).replace(/_/g, " ")}</span></div>
      </div>
      <p className="text-xs text-slate-700 mb-1">{recommendation.explanation}</p>
      <div className="text-[11px] text-slate-500 mb-1">Confidence: {(recommendation.confidence * 100).toFixed(0)}% (moderate)</div>
      {recommendation.uncertainties.length > 0 && (
        <div className="rounded bg-amber-50 border border-amber-200 text-amber-800 text-[11px] p-1.5 mb-2">
          ⚠ {recommendation.uncertainties.join(" ")}
        </div>
      )}

      {!decision && (
        <button
          disabled={busy}
          onClick={onAccept}
          className="text-[11px] px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          Accept recommendation
        </button>
      )}

      {decision && (
        <div className="mt-1 text-[11px] text-emerald-800">
          ✅ Decision captured: <span className="font-medium">{decision.summary}</span>
          {!outcomeResp && (
            <div className="mt-2">
              <button
                disabled={busy}
                onClick={onSimulate}
                className="text-[11px] px-2 py-1 rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
              >
                Simulate future outcome (demo-only)
              </button>
            </div>
          )}
        </div>
      )}

      {outcomeResp && (
        <div className="mt-2 rounded bg-white border border-emerald-200 p-2 text-[11px]">
          <div className="font-medium text-emerald-800 mb-1">📈 Simulated outcome: {outcomeResp.outcome.outcome_label}</div>
          {Object.entries(outcomeResp.outcome.metrics).map(([k, val]) => (
            <div key={k} className="flex justify-between text-slate-600">
              <span>{k.replace(/_/g, " ")}</span>
              <span className="font-medium text-slate-800">{String(val)}</span>
            </div>
          ))}
          {outcomeResp.pattern_id && (
            <div className="mt-1 text-purple-700">
              Portfolio pattern evidence: {outcomeResp.pattern_evidence_count_before} → {outcomeResp.pattern_evidence_count_after}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
