"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ACCENT, FAMILIES, SURFACE, TEXT } from "@/lib/design";
import { describeNode, edgeStyle } from "@/lib/nodeVisuals";
import type { GraphNodeData, GraphNodeType, GraphResponse } from "@/lib/types";
import { ApGraphNode, NODE_ANCHOR_Y, NODE_WIDTH } from "./ApGraphNode";

// Custom canvas (design_handoff v2 Sec.4): absolutely-positioned cards over
// one SVG for edges, deliberately not react-flow - the spec's exact bezier
// math, focus-tracing opacity states, and quiet control cluster are easier
// to hit faithfully hand-rolled than fought into react-flow's own zoom/pan/
// edge-rendering opinions.

// Conceptual layout stages - one per narrative beat, pitch ~330px per the
// handoff. creator/publisher and outcome/portfolio_pattern share a stage
// since they represent the same beat in the node inventory table.
const STAGES: GraphNodeType[][] = [
  ["team_member"],
  ["client"],
  ["creator", "publisher"],
  ["campaign"],
  ["memory_claim"],
  ["decision"],
  ["outcome", "portfolio_pattern"],
];
const COL_PITCH = 330;
const ROW_PITCH = 185;
const SPINE_Y = 175;
const CARD_HEIGHT_BUDGET = 220; // rough card height incl. padding/shadow, for world sizing
const WORLD_MARGIN = 60;

type Pos = { x: number; y: number };

function computeLayout(graph: GraphResponse): Record<string, Pos> {
  const pos: Record<string, Pos> = {};
  const placed = new Set<string>();
  STAGES.forEach((types, stageIdx) => {
    const inStage = graph.nodes
      .filter((n) => types.includes(n.node_type))
      .sort((a, b) => {
        const ta = types.indexOf(a.node_type);
        const tb = types.indexOf(b.node_type);
        return ta !== tb ? ta - tb : a.id.localeCompare(b.id);
      });
    const n = inStage.length;
    inStage.forEach((node, i) => {
      pos[node.id] = { x: stageIdx * COL_PITCH, y: SPINE_Y + (i - (n - 1) / 2) * ROW_PITCH };
      placed.add(node.id);
    });
  });
  // Defensive: any node type not covered by STAGES (shouldn't happen - the
  // union above is exhaustive over GraphNodeType) lands in one extra column.
  graph.nodes
    .filter((n) => !placed.has(n.id))
    .forEach((node, i) => {
      pos[node.id] = { x: STAGES.length * COL_PITCH, y: SPINE_Y + i * ROW_PITCH };
    });
  return pos;
}

function bezierPath(sx: number, sy: number, tx: number, ty: number): string {
  const dx = Math.max(70, (tx - sx) * 0.5);
  return `M ${sx},${sy} C ${sx + dx},${sy} ${tx - dx},${ty} ${tx},${ty}`;
}

const LEGEND_ITEMS: { color: string; label: string }[] = [
  { color: ACCENT.blue, label: "Client context & memory" },
  { color: ACCENT.amber, label: "Uncertainty & review" },
  { color: ACCENT.green, label: "Decision & outcome" },
  { color: ACCENT.purple, label: "Portfolio intelligence" },
  { color: ACCENT.historical, label: "Historical" },
];

interface IntelligenceGraphProps {
  graph: GraphResponse;
  /** Node ids called out by the last chat turn (referenced/supporting memories). */
  highlightedIds?: string[];
  selectedId: string | null;
  onSelectNode: (nodeId: string, node: GraphNodeData) => void;
  /** Node ids to bring into view after a mutation - memory approval,
   * SUPERSEDE, decision creation, outcome creation. */
  focusNodeIds?: string[];
}

export function IntelligenceGraph({ graph, highlightedIds = [], selectedId, onSelectNode, focusNodeIds = [] }: IntelligenceGraphProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [legendOpen, setLegendOpen] = useState(false);
  const [nodePos, setNodePos] = useState<Record<string, Pos>>({});
  const scrollRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ id: string; startX: number; startY: number; origX: number; origY: number } | null>(null);

  const layoutPos = useMemo(() => computeLayout(graph), [graph]);
  const nodesById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const highlightSet = useMemo(() => new Set(highlightedIds), [highlightedIds]);

  const posFor = useCallback((id: string): Pos => nodePos[id] ?? layoutPos[id] ?? { x: 0, y: 0 }, [nodePos, layoutPos]);

  const allPositions = Object.values(layoutPos);
  const minY = allPositions.length ? Math.min(...allPositions.map((p) => p.y)) : 0;
  const maxY = allPositions.length ? Math.max(...allPositions.map((p) => p.y)) : 0;
  const maxX = allPositions.length ? Math.max(...allPositions.map((p) => p.x)) : 0;
  const worldW = maxX + NODE_WIDTH + WORLD_MARGIN;
  const worldH = maxY - minY + CARD_HEIGHT_BUDGET + WORLD_MARGIN;
  const yShift = WORLD_MARGIN / 2 - minY;

  const focus = hoveredId ?? selectedId;
  const connected = useMemo(() => {
    if (!focus) return null;
    const set = new Set<string>([focus]);
    graph.edges.forEach((e) => {
      if (e.source === focus) set.add(e.target);
      if (e.target === focus) set.add(e.source);
    });
    return set;
  }, [focus, graph.edges]);
  const isolating = Boolean(focus);

  // Node drag: mousedown on a card starts it; delta divided by zoom so the
  // card tracks the cursor 1:1 regardless of current zoom level. Positions
  // live only in local component state (never persisted).
  useEffect(() => {
    function onMove(e: MouseEvent) {
      const d = dragRef.current;
      if (!d) return;
      const dx = (e.clientX - d.startX) / zoom;
      const dy = (e.clientY - d.startY) / zoom;
      setNodePos((p) => ({ ...p, [d.id]: { x: d.origX + dx, y: d.origY + dy } }));
    }
    function onUp() {
      dragRef.current = null;
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [zoom]);

  function startNodeDrag(id: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    const p = posFor(id);
    dragRef.current = { id, startX: e.clientX, startY: e.clientY, origX: p.x, origY: p.y };
  }

  // Re-frame the viewport around whatever just changed - not the whole
  // graph, which would zoom everything progressively smaller as the graph
  // grows over a demo. Deferred one frame so layout has settled first.
  useEffect(() => {
    if (focusNodeIds.length === 0) return;
    const el = scrollRef.current;
    if (!el) return;
    const raf = requestAnimationFrame(() => {
      const pts = focusNodeIds.map((id) => posFor(id));
      if (pts.length === 0) return;
      const cx = (Math.min(...pts.map((p) => p.x)) + Math.max(...pts.map((p) => p.x)) + NODE_WIDTH) / 2;
      const cy = (Math.min(...pts.map((p) => p.y)) + Math.max(...pts.map((p) => p.y)) + 150) / 2 + yShift;
      el.scrollTo({ left: cx * zoom - el.clientWidth / 2, top: cy * zoom - el.clientHeight / 2, behavior: "smooth" });
    });
    return () => cancelAnimationFrame(raf);
    // Only re-run when the focus target changes - not on every zoom/posFor
    // identity change, which would fight the user's own scrolling.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusNodeIds]);

  function zoomIn() {
    setZoom((z) => Math.min(1.5, +(z + 0.12).toFixed(2)));
  }
  function zoomOut() {
    setZoom((z) => Math.max(0.4, +(z - 0.12).toFixed(2)));
  }
  function fitToView() {
    const el = scrollRef.current;
    if (!el) {
      setZoom(1);
      return;
    }
    const scale = Math.min((el.clientWidth - 60) / worldW, (el.clientHeight - 60) / worldH, 1);
    setZoom(+Math.max(0.4, scale).toFixed(2));
    requestAnimationFrame(() => {
      el.scrollLeft = 0;
      el.scrollTop = 0;
    });
  }
  function resetLayout() {
    setZoom(1);
    setNodePos({});
    setHoveredId(null);
    const el = scrollRef.current;
    if (el) requestAnimationFrame(() => {
      el.scrollLeft = 0;
      el.scrollTop = 0;
    });
  }

  const iconBtn: React.CSSProperties = { width: 26, height: 26, border: "none", background: "transparent", color: TEXT.faint, cursor: "pointer" };

  return (
    <div style={{ position: "relative", height: "100%", width: "100%", background: SURFACE.app, minWidth: 420 }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.016) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.016) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
        }}
      />

      <div ref={scrollRef} className="ap-scroll" style={{ position: "absolute", inset: 0, overflow: "auto", padding: 72 }}>
        <div style={{ position: "relative", width: worldW * zoom, height: worldH * zoom }}>
          <div style={{ position: "relative", width: worldW, height: worldH, transform: `scale(${zoom})`, transformOrigin: "top left" }}>
            <svg width={worldW} height={worldH} style={{ position: "absolute", top: 0, left: 0, overflow: "visible" }}>
              <defs>
                {(Object.keys(FAMILIES) as (keyof typeof FAMILIES)[]).map((fam) => (
                  <marker key={fam} id={`mk-${fam}`} viewBox="0 0 10 10" refX={8} refY={5} markerWidth={6} markerHeight={6} orient="auto-start-reverse">
                    <path d="M0,0 L10,5 L0,10 z" fill={FAMILIES[fam].line} />
                  </marker>
                ))}
              </defs>
              {graph.edges.map((edge) => {
                const source = nodesById.get(edge.source);
                const target = nodesById.get(edge.target);
                if (!source || !target) return null;
                const sp = posFor(edge.source);
                const tp = posFor(edge.target);
                const sx = sp.x + NODE_WIDTH;
                const sy = sp.y + NODE_ANCHOR_Y + yShift;
                const tx = tp.x;
                const ty = tp.y + NODE_ANCHOR_Y + yShift;
                const targetFamily = describeNode(target, graph).family;
                const desc = edgeStyle(edge, targetFamily);
                const c = FAMILIES[desc.family];
                const touching = Boolean(connected && (edge.source === focus || edge.target === focus));
                const relevant = !connected || (connected.has(edge.source) && connected.has(edge.target));
                const showLabel = touching || desc.alwaysLabeled;
                const lx = (sx + tx) / 2;
                const ly = (sy + ty) / 2 - 7;
                return (
                  <g key={edge.id} style={{ opacity: isolating ? (relevant ? 1 : 0.12) : 0.5, transition: "opacity 0.3s" }}>
                    <path
                      d={bezierPath(sx, sy, tx, ty)}
                      fill="none"
                      stroke={c.line}
                      strokeWidth={touching ? 1.8 : 1.2}
                      strokeDasharray={desc.animated ? "5 5" : desc.dashed ? "4 4" : undefined}
                      markerEnd={`url(#mk-${desc.family})`}
                      style={desc.animated ? { animation: "edgeflow 0.7s linear infinite" } : undefined}
                    />
                    {showLabel && (
                      <text x={lx} y={ly} fontSize={11.5} fill={c.text} textAnchor="middle">
                        {desc.label}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>

            {graph.nodes.map((node) => {
              const p = posFor(node.id);
              const desc = describeNode(node, graph);
              const isFocus = node.id === focus;
              const inConnected = !connected || connected.has(node.id);
              const rawId = node.id.split(":").slice(1).join(":");
              const highlighted = highlightSet.has(node.id) || highlightSet.has(rawId);
              return (
                <ApGraphNode
                  key={node.id}
                  x={p.x}
                  y={p.y + yShift}
                  desc={desc}
                  isFocus={isFocus}
                  isDimmed={isolating && !inConnected}
                  highlighted={highlighted}
                  onEnter={() => setHoveredId(node.id)}
                  onLeave={() => setHoveredId(null)}
                  onClick={() => onSelectNode(node.id, node)}
                  onMouseDown={(e) => startNodeDrag(node.id, e)}
                />
              );
            })}
          </div>
        </div>
      </div>

      <div style={{ position: "absolute", bottom: 20, right: 20, display: "flex", alignItems: "center", gap: 14 }}>
        <button onClick={() => setLegendOpen((v) => !v)} style={{ fontSize: 12, color: TEXT.faint, background: "transparent", border: "none", cursor: "pointer", padding: 4 }}>
          {legendOpen ? "Hide legend" : "Legend"}
        </button>
        <div style={{ display: "flex", gap: 2 }}>
          <button onClick={zoomOut} title="Zoom out" style={{ ...iconBtn, fontSize: 15 }}>
            −
          </button>
          <button onClick={zoomIn} title="Zoom in" style={{ ...iconBtn, fontSize: 15 }}>
            +
          </button>
          <button onClick={fitToView} title="Fit to view" style={{ ...iconBtn, fontSize: 12 }}>
            ⛶
          </button>
          <button onClick={resetLayout} title="Reset layout" style={{ ...iconBtn, fontSize: 12 }}>
            ↺
          </button>
        </div>
      </div>

      {legendOpen && (
        <div
          style={{
            position: "absolute",
            bottom: 56,
            right: 20,
            background: SURFACE.raised,
            borderRadius: 10,
            padding: "16px 18px",
            fontSize: 13,
            color: TEXT.secondary,
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {LEGEND_ITEMS.map((item) => (
              <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 9 }}>
                <span style={{ width: 7, height: 7, borderRadius: 2, background: item.color }} />
                {item.label}
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, paddingTop: 11, borderTop: `1px solid ${SURFACE.separatorInner2}`, color: TEXT.faint, fontSize: 12 }}>
            Select a node to reveal its relationships
          </div>
        </div>
      )}
    </div>
  );
}
