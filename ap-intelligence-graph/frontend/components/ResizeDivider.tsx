"use client";

import { SURFACE } from "@/lib/design";

/**
 * A draggable panel/pane divider. Visually a 1px line (matching the spec's
 * "Separators: 1px #151b26 ... which are also the resize handles"), but with
 * a wider invisible hit target (negative margins pull the extra thickness
 * back over the neighboring content without shifting layout) - a bare 1px
 * element is nearly impossible to grab precisely with a real mouse.
 */
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
