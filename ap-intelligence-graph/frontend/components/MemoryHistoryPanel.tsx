"use client";

import { ACCENT, FONT_MONO, TEXT, predicateLabel, sentenceCase } from "@/lib/design";
import type { MemoryHistoryEntry, MemoryHistoryResponse, WhatChangedSummary } from "@/lib/types";

function fmtDate(iso: string | null): string {
  if (!iso) return "present";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" }).toUpperCase();
}

const STATUS_LABEL: Record<string, string> = {
  active: "ACTIVE",
  superseded: "SUPERSEDED",
  expired: "EXPIRED",
  needs_review: "NEEDS REVIEW",
  low_confidence: "LOW CONFIDENCE",
  deprecated: "DEPRECATED",
  rejected: "REJECTED",
};

function sourceLine(source: { type: string; [k: string]: unknown }): string | null {
  if (typeof source.message_excerpt === "string" && source.message_excerpt) return `“${source.message_excerpt}”`;
  if (typeof source.campaign_label === "string" && source.campaign_label) return `Campaign review — ${source.campaign_label}`;
  if (source.type) return sentenceCase(String(source.type));
  return null;
}

function HistoryEntryRow({ entry, onHighlight }: { entry: MemoryHistoryEntry; onHighlight?: (ids: string[]) => void }) {
  const isCurrent = entry.status === "active";
  const src = sourceLine(entry.source);
  return (
    <div
      onClick={onHighlight ? () => onHighlight([`memory_claim:${entry.claim_id}`]) : undefined}
      style={{
        cursor: onHighlight ? "pointer" : "default",
        padding: "12px 14px",
        borderRadius: 8,
        background: isCurrent ? "rgba(79,185,141,0.06)" : "transparent",
        border: `1px solid ${isCurrent ? "rgba(79,185,141,0.18)" : SURFACE_BORDER}`,
      }}
    >
      <div style={{ fontSize: 11, letterSpacing: "0.08em", color: TEXT.faint, marginBottom: 4 }}>{fmtDate(entry.valid_from)}</div>
      <div style={{ fontSize: 14.5, fontWeight: isCurrent ? 600 : 500, color: isCurrent ? TEXT.primary : TEXT.secondary2, marginBottom: 6 }}>
        {sentenceCase(entry.value)}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span
          style={{
            fontSize: 10.5, letterSpacing: "0.06em", fontFamily: FONT_MONO,
            color: isCurrent ? ACCENT.green : entry.status === "needs_review" ? ACCENT.amber : TEXT.faint,
          }}
        >
          {STATUS_LABEL[entry.status] ?? entry.status.toUpperCase()}
        </span>
        <span style={{ fontSize: 11.5, color: TEXT.faint }}>
          {fmtDate(entry.valid_from)} – {entry.valid_to ? fmtDate(entry.valid_to) : "present"}
        </span>
        <span style={{ fontSize: 11.5, color: TEXT.faint }}>confidence {entry.confidence.toFixed(2)}</span>
        {entry.synthetic && <span style={{ fontSize: 10.5, letterSpacing: "0.06em", color: "#6b6288" }}>SYNTHETIC</span>}
      </div>
      {src && <div style={{ fontSize: 12.5, color: TEXT.metadata, marginTop: 6, lineHeight: 1.5 }}>Source: {src}</div>}
    </div>
  );
}

const SURFACE_BORDER = "#151b26";

export function MemoryHistoryPanel({ history, onHighlight }: { history: MemoryHistoryResponse; onHighlight?: (ids: string[]) => void }) {
  const { timeline } = history;
  const hasChange = timeline.changes.length > 1;

  return (
    <>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 4 }}>WHAT CHANGED</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: TEXT.primary, marginBottom: 2 }}>{timeline.subject.name}</div>
      <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 16 }}>{predicateLabel(timeline.predicate)}</div>

      {timeline.changes.length === 0 ? (
        <div style={{ fontSize: 13.5, color: TEXT.faint, fontStyle: "italic", marginBottom: 16 }}>No governed change history exists for this topic yet.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 16 }}>
          {timeline.changes.map((entry, i) => (
            <div key={entry.claim_id}>
              <HistoryEntryRow entry={entry} onHighlight={onHighlight} />
              {i < timeline.changes.length - 1 && (
                <div style={{ textAlign: "center", color: TEXT.faint, fontSize: 13, padding: "4px 0" }}>↓</div>
              )}
            </div>
          ))}
        </div>
      )}

      {!hasChange && (
        <div style={{ fontSize: 12.5, color: TEXT.faint, fontStyle: "italic", marginBottom: 16 }}>
          {timeline.changes.length === 1 ? "Nothing has superseded this yet." : ""}
        </div>
      )}

      <div style={{ borderTop: `1px solid ${SURFACE_BORDER}`, paddingTop: 14 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint }}>CURRENT STATE</div>
          <span style={{ fontSize: 10.5, letterSpacing: "0.06em", color: ACCENT.purple, fontFamily: FONT_MONO }}>MODEL SYNTHESIS</span>
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.55, color: TEXT.primary, marginBottom: hasChange ? 10 : 0 }}>{history.current_state}</div>
        {hasChange && history.summary && (
          <div style={{ fontSize: 13.5, lineHeight: 1.55, color: TEXT.secondary2 }}>{history.summary}</div>
        )}
      </div>
    </>
  );
}

export function WhatChangedPanel({ summary, onHighlight }: { summary: WhatChangedSummary; onHighlight?: (ids: string[]) => void }) {
  return (
    <>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 4 }}>WHAT CHANGED</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: TEXT.primary, marginBottom: 16 }}>{summary.subject.name}</div>

      {summary.changed_dimensions.length === 0 ? (
        <div style={{ fontSize: 13.5, color: TEXT.faint, fontStyle: "italic" }}>No governed change history exists for {summary.subject.name} yet.</div>
      ) : (
        <>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 12 }}>
            {summary.changed_dimensions.length} governed belief{summary.changed_dimensions.length === 1 ? "" : "s"} changed
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {summary.changed_dimensions.map((d) => (
              <div
                key={d.predicate}
                onClick={onHighlight ? () => onHighlight([`partner:${d.subject_id}`, `client:${d.subject_id}`]) : undefined}
                style={{ cursor: onHighlight ? "pointer" : "default" }}
              >
                <div style={{ fontSize: 12.5, letterSpacing: "0.05em", color: TEXT.metadata, marginBottom: 4 }}>{predicateLabel(d.predicate).toUpperCase()}</div>
                <div style={{ fontSize: 14, color: TEXT.secondary2 }}>
                  {sentenceCase(d.old_value)} <span style={{ color: TEXT.faint }}>→</span> <span style={{ color: TEXT.primary, fontWeight: 600 }}>{sentenceCase(d.new_value)}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
