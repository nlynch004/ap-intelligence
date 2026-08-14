"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ActivityEvent, GraphNodeData, GraphResponse } from "@/lib/types";
import { ChatPanel } from "@/components/ChatPanel";
import { IntelligenceGraph } from "@/components/IntelligenceGraph";
import { MemoryInspector } from "@/components/MemoryInspector";
import { ActivityFeed } from "@/components/ActivityFeed";

const CLIENT_ID = "northwind";

export default function Home() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [g, a] = await Promise.all([api.getGraph(CLIENT_ID), api.getActivity(CLIENT_ID)]);
      setGraph(g);
      setActivity(a);
      setLoadError(null);
    } catch (err) {
      setLoadError(
        `Could not reach the backend at ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}. ` +
          `Is it running? (${(err as Error).message})`,
      );
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function handleSelectNode(nodeId: string, node: GraphNodeData) {
    setSelectedId(nodeId);
    setSelectedNode(node);
  }

  function handleHighlight(ids: string[]) {
    setHighlightedIds(ids);
  }

  if (loadError) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-md text-center text-sm text-slate-500">
          <div className="text-2xl mb-2">⚠️</div>
          {loadError}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      <header className="border-b border-slate-200 bg-white px-4 py-2.5 flex items-baseline gap-2">
        <h1 className="text-sm font-bold text-slate-900">AP Intelligence Graph</h1>
        <span className="text-xs text-slate-400">The living memory of AP&apos;s partnership decisions, relationships, and outcomes.</span>
      </header>

      <div className="flex-1 flex min-h-0">
        <section className="w-[30%] min-w-[320px] border-r border-slate-200 bg-white">
          <ChatPanel clientId={CLIENT_ID} graph={graph} onAfterMutation={refresh} onHighlight={handleHighlight} />
        </section>

        <section className="w-[45%] bg-slate-50 relative">
          {graph ? (
            <IntelligenceGraph graph={graph} highlightedIds={highlightedIds} selectedId={selectedId} onSelectNode={handleSelectNode} />
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">Loading graph…</div>
          )}
        </section>

        <section className="w-[25%] min-w-[280px] border-l border-slate-200 bg-white flex flex-col min-h-0">
          <div className="border-b border-slate-200" style={{ height: "55%" }}>
            <MemoryInspector node={selectedNode} />
          </div>
          <div className="flex-1 min-h-0">
            <ActivityFeed events={activity} />
          </div>
        </section>
      </div>
    </div>
  );
}
