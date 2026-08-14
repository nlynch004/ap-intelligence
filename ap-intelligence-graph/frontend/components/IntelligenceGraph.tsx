"use client";

import { useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  useEdgesState,
  useNodesState,
  type Edge,
} from "@xyflow/react";
import type { GraphNodeData, GraphNodeType, GraphResponse } from "@/lib/types";
import { ApGraphNode, type ApFlowNode } from "./ApGraphNode";

const nodeTypes = { apNode: ApGraphNode };

// Deterministic columnar layout - legible for graphs this size without
// pulling in a dagre dependency (spec Sec.23: prioritize reliability).
const COLUMN_ORDER: GraphNodeType[] = [
  "team_member",
  "client",
  "creator",
  "publisher",
  "campaign",
  "memory_claim",
  "decision",
  "outcome",
  "portfolio_pattern",
];
const COLUMN_X: Record<string, number> = {};
COLUMN_ORDER.forEach((t, i) => (COLUMN_X[t] = i * 260));

const ROW_HEIGHT = 92;

const RELATIONSHIP_STYLE: Record<string, { stroke: string; dashed?: boolean; animated?: boolean }> = {
  SUPERSEDES: { stroke: "#dc2626", dashed: true },
  HAS_RISK: { stroke: "#d97706", dashed: true },
  MOTIVATED_BY: { stroke: "#2563eb", dashed: true },
  MADE_DECISION: { stroke: "#059669" },
  RESULTED_IN: { stroke: "#059669", animated: true },
  SUPPORTS: { stroke: "#7c3aed" },
  APPLIES_TO: { stroke: "#64748b" },
  HAS_CAMPAIGN: { stroke: "#64748b" },
  HAS_STRATEGY: { stroke: "#2563eb" },
  HAS_GOAL: { stroke: "#2563eb" },
  HAS_RELATIONSHIP: { stroke: "#64748b" },
  MANAGES: { stroke: "#64748b" },
  WORKED_WITH: { stroke: "#64748b" },
};

function layout(graph: GraphResponse, highlightedIds: Set<string>, selectedId: string | null): { nodes: ApFlowNode[]; edges: Edge[] } {
  const columnCounts: Record<string, number> = {};
  const nodes: ApFlowNode[] = graph.nodes.map((n: GraphNodeData) => {
    const col = COLUMN_X[n.node_type] ?? 999;
    const row = columnCounts[n.node_type] ?? 0;
    columnCounts[n.node_type] = row + 1;
    const rawId = n.id.split(":").slice(1).join(":");
    return {
      id: n.id,
      type: "apNode",
      position: { x: col, y: row * ROW_HEIGHT },
      data: { ...n, highlighted: highlightedIds.has(n.id) || highlightedIds.has(rawId), selected: n.id === selectedId },
    };
  });

  const edges: Edge[] = graph.edges.map((e) => {
    const style = RELATIONSHIP_STYLE[e.relationship] ?? { stroke: "#94a3b8" };
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.relationship.replace(/_/g, " ").toLowerCase(),
      labelStyle: { fontSize: 9, fill: "#64748b" },
      labelBgStyle: { fill: "#f8fafc", fillOpacity: 0.9 },
      style: { stroke: style.stroke, strokeDasharray: style.dashed ? "4 3" : undefined, strokeWidth: 1.4 },
      animated: style.animated,
      markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke, width: 14, height: 14 },
    };
  });

  return { nodes, edges };
}

export function IntelligenceGraph({
  graph,
  highlightedIds = [],
  selectedId,
  onSelectNode,
}: {
  graph: GraphResponse;
  highlightedIds?: string[];
  selectedId: string | null;
  onSelectNode: (nodeId: string, node: GraphNodeData) => void;
}) {
  const highlightSet = useMemo(() => new Set(highlightedIds), [highlightedIds]);
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => layout(graph, highlightSet, selectedId),
    [graph, highlightSet, selectedId],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState<ApFlowNode>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelectNode(node.id, (node.data as ApFlowNode["data"]))}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} size={1} color="#e2e8f0" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
