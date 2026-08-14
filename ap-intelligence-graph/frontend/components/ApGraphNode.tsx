"use client";

import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { GraphNodeData } from "@/lib/types";
import { visualFor } from "@/lib/nodeVisuals";

export type ApNodeData = GraphNodeData & {
  highlighted?: boolean;
  selected?: boolean;
  [key: string]: unknown;
};

export type ApFlowNode = Node<ApNodeData, "apNode">;

export function ApGraphNode({ data }: NodeProps<ApFlowNode>) {
  const v = visualFor(data);
  const highlighted = data.highlighted;
  const selected = data.selected;

  return (
    <div
      className={[
        "rounded-lg border px-3 py-2 shadow-sm text-xs min-w-[160px] max-w-[220px] transition-all",
        v.bg,
        v.border,
        v.dashed ? "border-dashed" : "border-solid",
        v.faded ? "opacity-50" : "opacity-100",
        highlighted ? "ring-2 ring-offset-1 ring-blue-500 shadow-md" : "",
        selected ? "ring-2 ring-offset-1 ring-slate-900" : "",
      ].join(" ")}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-1.5 !h-1.5" />
      <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-1.5 !h-1.5" />
      <div className="flex items-center gap-1.5">
        <span className="text-sm leading-none">{v.icon}</span>
        <span className={`font-medium leading-tight ${v.accent}`}>{data.label}</span>
      </div>
      {v.badge && (
        <div className={`mt-1 inline-block rounded-full px-1.5 py-0.5 text-[10px] font-medium bg-white/70 ${v.accent}`}>
          {v.badge}
        </div>
      )}
      {data.node_type === "memory_claim" && typeof data.data?.confidence === "number" && (
        <div className="mt-1 text-[10px] text-slate-500">confidence {(data.data.confidence as number).toFixed(2)}</div>
      )}
    </div>
  );
}
