"use client";

import type { ActivityEvent } from "@/lib/types";

const EVENT_ICON: Record<string, string> = {
  CREATE: "🆕",
  UPDATE: "✏️",
  SUPERSEDE: "🔁",
  DECISION: "✅",
  OUTCOME: "📈",
  PROMOTE: "📊",
  REJECT: "🚫",
  SEED: "🌱",
};

export function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="p-3 overflow-y-auto h-full">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Activity</h3>
      {events.length === 0 && <div className="text-xs text-slate-400 italic">No activity yet.</div>}
      <ul className="space-y-2">
        {[...events].reverse().map((e) => (
          <li key={e.id} className="text-xs">
            <div className="flex items-start gap-1.5">
              <span>{EVENT_ICON[e.event_type] ?? "•"}</span>
              <div className="min-w-0">
                <div className="text-[10px] text-slate-400">
                  {e.created_at.slice(11, 19)} · {e.event_type}
                </div>
                <div className="text-slate-700 leading-snug">{e.summary}</div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
