"use client";

import { SURFACE } from "@/lib/design";

export function ResizeDivider({ direction, onMouseDown }: { direction: "row" | "col"; onMouseDown: (e: React.MouseEvent) => void }) {
  if (direction === "row") {
    return (
      <div
        onMouseDown={onMouseDown}
        style={{ flex: "none", height: 7, marginTop: -3, marginBottom: -3, cursor: "row-resize", display: "flex", alignItems: "center", position: "relative", zIndex: 1 }}
      >
        <div style={{ height: 1, width: "100%", background: SURFACE.separator }} />
      </div>
    );
  }
  return (
    <div
      onMouseDown={onMouseDown}
      style={{ flex: "none", width: 7, marginLeft: -3, marginRight: -3, cursor: "col-resize", display: "flex", justifyContent: "center", position: "relative", zIndex: 1 }}
    >
      <div style={{ width: 1, height: "100%", background: SURFACE.separator }} />
    </div>
  );
}
