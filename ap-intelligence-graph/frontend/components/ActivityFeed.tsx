"use client";

import { ACCENT, FONT_MONO, SURFACE, TEXT, titleCase } from "@/lib/design";
import type { ActivityEvent } from "@/lib/types";

// Raw event types (backend/app/memory/operations.py, app/routers/decisions.py)
// are never shown directly - the human title carries the meaning (design_handoff
// v2 Sec.5: "Raw event types are not displayed").
const EVENT_TITLE: Record<string, string> = {
  SEED: "Account graph loaded",
  CREATE: "Memory recorded",
  UPDATE: "Belief refined",
  SUPERSEDE: "Strategy updated",
  DECISION: "Decision captured",
  OUTCOME: "Outcome recorded",
  PROMOTE: "Portfolio pattern updated",
  REJECT: "Candidate rejected",
};

const EVENT_DOT: Record<string, string> = {
  SEED: ACCENT.historical,
  CREATE: ACCENT.blue,
  UPDATE: ACCENT.blue,
  SUPERSEDE: "#8896ac",
  DECISION: ACCENT.green,
  OUTCOME: ACCENT.purple,
  PROMOTE: ACCENT.purple,
  REJECT: TEXT.faint,
};

export function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  const ordered = [...events].reverse();

  return (
    <div className="ap-scroll" style={{ flex: 1, overflowY: "auto", padding: 22, borderTop: `1px solid ${SURFACE.separatorInner}`, minHeight: 0 }}>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 18 }}>ACTIVITY</div>
      {ordered.length === 0 && <div style={{ fontSize: 13, color: TEXT.secondary2, fontStyle: "italic" }}>No activity yet.</div>}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {ordered.map((e) => (
          <div key={e.id} style={{ display: "flex", gap: 14, animation: "fadeup 0.4s ease" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: "none", paddingTop: 5 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: EVENT_DOT[e.event_type] ?? TEXT.faint, flex: "none" }} />
              <span style={{ width: 1, flex: 1, background: SURFACE.timelineRail, minHeight: 26 }} />
            </div>
            <div style={{ minWidth: 0, paddingBottom: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: TEXT.strongSecondary }}>{EVENT_TITLE[e.event_type] ?? titleCase(e.event_type)}</div>
              <div style={{ fontSize: 13, color: TEXT.secondary2, lineHeight: 1.5, marginTop: 2 }}>{e.summary}</div>
              <div style={{ fontSize: 12, fontFamily: FONT_MONO, color: TEXT.faint, marginTop: 5 }}>{e.created_at.slice(11, 19)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
