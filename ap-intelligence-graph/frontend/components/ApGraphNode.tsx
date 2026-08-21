"use client";

import { FAMILIES, SURFACE, TEXT } from "@/lib/design";
import type { NodeDescription } from "@/lib/nodeVisuals";

export const NODE_WIDTH = 250;
export const NODE_ANCHOR_Y = 52;

export function ApGraphNode({
  x,
  y,
  desc,
  isFocus,
  isDimmed,
  highlighted,
  onEnter,
  onLeave,
  onClick,
  onMouseDown,
}: {
  x: number;
  y: number;
  desc: NodeDescription;
  isFocus: boolean;
  isDimmed: boolean;
  highlighted?: boolean;
  onEnter: () => void;
  onLeave: () => void;
  onClick: () => void;
  onMouseDown: (e: React.MouseEvent) => void;
}) {
  const c = FAMILIES[desc.family];
  const bg = isFocus ? c.node : desc.historical ? SURFACE.nodeHistorical : SURFACE.nodeResting;
  const border = isFocus ? c.border : SURFACE.nodeBorderResting;
  const typeColor = desc.historical ? "#4d596d" : c.text;
  const titleColor = desc.historical ? TEXT.historicalTitle : TEXT.primary;
  const statusColor = desc.historical ? TEXT.historicalStatus : c.text;
  const restingOpacity = desc.historical ? 0.7 : 1;
  const focusRing = isFocus ? `0 0 0 1px ${c.border}, 0 0 0 4px ${c.glow}` : "none";
  const highlightRing = highlighted ? `0 0 0 2px #5b9fd4` : "none";
  const boxShadow = [focusRing, highlightRing].filter((s) => s !== "none").join(", ") || "none";

  return (
    <div
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onClick={onClick}
      onMouseDown={onMouseDown}
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: NODE_WIDTH,
        cursor: "grab",
        userSelect: "none",
        borderRadius: 10,
        padding: "14px 16px",
        transition: "opacity 0.3s, box-shadow 0.3s, background 0.3s",
        opacity: isDimmed ? 0.3 : restingOpacity,
        background: bg,
        border: `1px solid ${border}`,
        boxShadow,
      }}
    >
      <div style={{ fontSize: 12, color: typeColor, marginBottom: 7 }}>{desc.typeLabel}</div>
      <div style={{ fontSize: 15.5, fontWeight: 600, lineHeight: 1.35, color: titleColor, whiteSpace: "pre-line" }}>
        {desc.title}
      </div>
      {desc.detail && <div style={{ fontSize: 13, color: TEXT.metadata, marginTop: 4, lineHeight: 1.45 }}>{desc.detail}</div>}
      {(desc.statusText || desc.synthetic) && (
        <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {desc.statusText && <span style={{ fontSize: 12, color: statusColor }}>{desc.statusText}</span>}
          {desc.synthetic && (
            <span
              title="Fictional demo data - not a real AP client, creator, or decision."
              style={{ fontSize: 10, letterSpacing: "0.08em", color: "#6b6288" }}
            >
              SYNTHETIC
            </span>
          )}
        </div>
      )}
    </div>
  );
}
