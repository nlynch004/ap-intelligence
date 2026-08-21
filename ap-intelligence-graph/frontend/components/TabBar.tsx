"use client";

import { SURFACE, TEXT } from "@/lib/design";

export type AppTab = "demo" | "guide";

const TABS: { id: AppTab; label: string }[] = [
  { id: "demo", label: "Live Demo" },
  { id: "guide", label: "Discussion Guide" },
];

export function TabBar({
  active, onChange, onLogout,
}: {
  active: AppTab;
  onChange: (tab: AppTab) => void;
  onLogout?: () => void;
}) {
  return (
    <div
      style={{
        flex: "none",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 2,
        padding: "8px 24px",
        background: SURFACE.app,
        borderBottom: `1px solid ${SURFACE.separator}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
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
      {onLogout && (
        <button
          onClick={onLogout}
          style={{ fontSize: 12, fontWeight: 600, padding: "6px 12px", borderRadius: 7, border: "none", background: "transparent", color: TEXT.faint, cursor: "pointer" }}
        >
          Log out
        </button>
      )}
    </div>
  );
}
