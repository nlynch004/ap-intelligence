"use client";

import type { GraphNodeData } from "@/lib/types";
import { visualFor } from "@/lib/nodeVisuals";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 py-1 text-xs border-b border-slate-100 last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-800 text-right">{children}</span>
    </div>
  );
}

function fmtVal(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return v.toLocaleString();
  return String(v).replace(/_/g, " ");
}

export function MemoryInspector({ node }: { node: GraphNodeData | null }) {
  if (!node) {
    return (
      <div className="p-4 text-sm text-slate-400 italic">
        Click a node in the graph to inspect its memory metadata, source, and status.
      </div>
    );
  }

  const v = visualFor(node);
  const d = node.data ?? {};

  return (
    <div className="p-4 overflow-y-auto h-full">
      <div className="flex items-center gap-2 mb-1">
        <span>{v.icon}</span>
        <h3 className="font-semibold text-sm text-slate-900">{node.label}</h3>
      </div>
      <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-3">{node.node_type.replace(/_/g, " ")}</div>

      {node.node_type === "memory_claim" && (
        <div>
          <Row label="Claim class">{fmtVal(d.claim_class)}</Row>
          <Row label="Status">{fmtVal(d.status)}</Row>
          <Row label="Confidence">{typeof d.confidence === "number" ? (d.confidence as number).toFixed(2) : "—"}</Row>
          <Row label="Authority">{typeof d.authority_score === "number" ? (d.authority_score as number).toFixed(2) : "—"}</Row>
          <Row label="Synthetic">{fmtVal(d.synthetic)}</Row>
          <Row label="Valid from">{fmtVal(d.valid_from)}</Row>
          <Row label="Valid to">{fmtVal(d.valid_to)}</Row>
          {Boolean((d.source as Record<string, unknown> | undefined)?.type) && (
            <Row label="Source">{fmtVal((d.source as Record<string, unknown>).type)}</Row>
          )}
          {Array.isArray(d.supersedes) && (d.supersedes as string[]).length > 0 && (
            <Row label="Supersedes">{(d.supersedes as string[]).join(", ")}</Row>
          )}
          {Boolean(d.superseded_by) && <Row label="Superseded by">{fmtVal(d.superseded_by)}</Row>}
          {node.status === "needs_review" && (
            <div className="mt-3 rounded bg-amber-50 border border-amber-200 text-amber-800 text-xs p-2">
              This is an unverified hypothesis, not a confirmed fact. It requires human review before being
              treated as ground truth.
            </div>
          )}
          {node.status === "superseded" && (
            <div className="mt-3 rounded bg-slate-50 border border-slate-200 text-slate-600 text-xs p-2">
              Historical belief. Excluded from normal retrieval, but preserved for audit.
            </div>
          )}
        </div>
      )}

      {node.node_type === "campaign" && (
        <div>
          <Row label="Flat fee">${fmtVal(d.flat_fee)}</Row>
          <Row label="Link clicks">{fmtVal(d.link_clicks)}</Row>
          <Row label="Code redemptions">{fmtVal(d.code_redemptions)}</Row>
          <Row label="Attributed revenue">${fmtVal(d.attributed_revenue)}</Row>
        </div>
      )}

      {(node.node_type === "creator" || node.node_type === "publisher") && (
        <div>
          <Row label="Platform">{fmtVal(d.platform)}</Row>
          <Row label="Synthetic">{fmtVal(d.synthetic)}</Row>
        </div>
      )}

      {node.node_type === "decision" && (
        <div>
          <Row label="Status">{fmtVal(node.status)}</Row>
          {d.terms != null && (
            <div className="mt-2 rounded bg-emerald-50 border border-emerald-200 p-2 text-xs">
              {Object.entries(d.terms as Record<string, unknown>).map(([k, val]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-emerald-700">{fmtVal(k)}</span>
                  <span className="text-emerald-900 font-medium">{fmtVal(val)}</span>
                </div>
              ))}
            </div>
          )}
          {Boolean(d.rationale) && <p className="mt-2 text-xs text-slate-600">{fmtVal(d.rationale)}</p>}
        </div>
      )}

      {node.node_type === "outcome" && (
        <div>
          <Row label="Result">{fmtVal(node.status)}</Row>
          <Row label="Simulated">{fmtVal(d.is_simulated)}</Row>
          {d.metrics != null && (
            <div className="mt-2 rounded bg-emerald-50 border border-emerald-200 p-2 text-xs">
              {Object.entries(d.metrics as Record<string, unknown>).map(([k, val]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-emerald-700">{fmtVal(k)}</span>
                  <span className="text-emerald-900 font-medium">{fmtVal(val)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {node.node_type === "portfolio_pattern" && (
        <div>
          <div className="mb-2 rounded bg-purple-50 border border-purple-200 text-purple-800 text-[11px] p-2">
            Synthetic AP portfolio pattern - clearly labeled, not real client data.
          </div>
          <Row label="Evidence count">{fmtVal(d.evidence_count)}</Row>
          <Row label="Positive outcomes">{fmtVal(d.positive_outcomes)}</Row>
          <Row label="Flat-fee success">{typeof d.flat_fee_success_rate === "number" ? `${Math.round((d.flat_fee_success_rate as number) * 100)}%` : "—"}</Row>
          <Row label="Hybrid success">{typeof d.hybrid_success_rate === "number" ? `${Math.round((d.hybrid_success_rate as number) * 100)}%` : "—"}</Row>
          {Boolean(d.description) && <p className="mt-2 text-xs text-slate-600">{fmtVal(d.description)}</p>}
          {Array.isArray(d.strongest_conditions) && (
            <ul className="mt-2 list-disc list-inside text-xs text-slate-600 space-y-0.5">
              {(d.strongest_conditions as string[]).map((c) => (
                <li key={c}>{fmtVal(c)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
