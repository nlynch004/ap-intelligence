"use client";

import { SURFACE, TEXT } from "@/lib/design";

export type AppTab = "demo" | "guide";

const TABS: { id: AppTab; label: string }[] = [
  { id: "demo", label: "Live Demo" },
  { id: "guide", label: "Discussion Guide" },
];

/**
 * Restrained top-level segmented control between the live demo and the
 * post-demo Discussion Guide. Purely a view toggle - app/page.tsx keeps both
 * views mounted at all times and switches which one is painted, so this
 * component never causes the demo to reset (see app/page.tsx).
 */
export function TabBar({ active, onChange }: { active: AppTab; onChange: (tab: AppTab) => void }) {
  return (
    <div
      style={{
        flex: "none",
        display: "flex",
        alignItems: "center",
        gap: 2,
        padding: "8px 24px",
        background: SURFACE.app,
        borderBottom: `1px solid ${SURFACE.separator}`,
      }}
    >
      {TABS.map((t) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            style={{
              fontSize: 12.5,
              fontWeight: 600,
              padding: "6px 14px",
              borderRadius: 7,
              border: "none",
              cursor: "pointer",
              background: isActive ? SURFACE.activeRow : "transparent",
              color: isActive ? TEXT.primary : TEXT.secondary2,
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
