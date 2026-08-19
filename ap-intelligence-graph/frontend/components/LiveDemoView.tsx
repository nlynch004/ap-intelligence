"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { ACCENT, SURFACE, TEXT } from "@/lib/design";
import { withDerivedEdges, withoutRelationshipClaims } from "@/lib/graphAugment";
import type { ActivityEvent, GraphNodeData, GraphResponse, ScenarioComparisonRef } from "@/lib/types";
import { ChatPanel } from "@/components/ChatPanel";
import { IntelligenceGraph } from "@/components/IntelligenceGraph";
import { MemoryInspector } from "@/components/MemoryInspector";
import { ActivityFeed } from "@/components/ActivityFeed";
import { ResetDemoButton } from "@/components/ResetDemoButton";
import { ResizeDivider } from "@/components/ResizeDivider";

const CLIENT_ID = "northwind";

// Panel resize bounds (design_handoff v2 "Shell / layout" + "Resize panels").
const CHAT_MIN = 240;
const CHAT_MAX = 560;
const CHAT_DEFAULT_CAP = 380;
const CHAT_DEFAULT_FRAC = 0.28;
const INSPECTOR_MIN = 220;
const INSPECTOR_MAX = 520;
const INSPECTOR_DEFAULT_CAP = 330;
const INSPECTOR_DEFAULT_FRAC = 0.23;
// Bounds for the draggable divider between the inspector's Context block and
// its Activity feed below it (mirrors ChatPanel's steps/conversation divider).
const INSPECTOR_TOP_DEFAULT_H = 340;
const INSPECTOR_TOP_MIN_H = 160;
const INSPECTOR_TOP_MAX_H = 700;

async function loadDashboardData(clientId: string): Promise<{ graph: GraphResponse; activity: ActivityEvent[] }> {
  const [graph, activity] = await Promise.all([api.getGraph(clientId), api.getActivity(clientId)]);
  return { graph: withDerivedEdges(withoutRelationshipClaims(graph)), activity };
}

/** Header breadcrumb, e.g. "Creator renewal / Summit Sisters" - derived from
 * whatever partner the client's open campaign(s) involve, never hardcoded to
 * this one demo's names. */
function headerContext(graph: GraphResponse | null): string {
  if (!graph) return "";
  const campaign = graph.nodes.find((n) => n.node_type === "campaign");
  const partnerName =
    (campaign?.data.partner_name as string | undefined) ??
    graph.nodes.find((n) => n.node_type === "creator" || n.node_type === "publisher")?.label;
  return partnerName ? `Creator renewal / ${partnerName}` : "Creator renewal";
}

/**
 * The full live-demo workspace (graph + chat + inspector), unchanged from
 * the pre-tab version of this app other than living at `height: "100%"`
 * instead of `100vh` - it's now a flex child under the top-level tab bar
 * (see app/page.tsx) rather than the viewport-filling root. Mounted for the
 * lifetime of the app (app/page.tsx toggles visibility, never unmounts this
 * component) so switching to the Discussion Guide tab and back never resets
 * this component's state or re-fetches the graph.
 */
export function LiveDemoView() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<string[]>([]);
  const [focusNodeIds, setFocusNodeIds] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [demoEpoch, setDemoEpoch] = useState(0);
  const [reviewCampaignRequest, setReviewCampaignRequest] = useState<{ campaignId: string; nonce: number } | null>(null);
  const [partnerBriefRequest, setPartnerBriefRequest] = useState<{ partnerId: string; nonce: number } | null>(null);
  const [memoryHistoryRequest, setMemoryHistoryRequest] = useState<{ subjectType: string; subjectId: string; predicate: string; nonce: number } | null>(null);
  const [whatChangedRequest, setWhatChangedRequest] = useState<{ subjectType: string; subjectId: string; nonce: number } | null>(null);
  const [scenarioComparisonRequest, setScenarioComparisonRequest] = useState<{ partnerId: string; currentAsk: number; nonce: number } | null>(null);
  const [planBuildRequest, setPlanBuildRequest] = useState<{ planningPeriod: string | undefined; nonce: number } | null>(null);
  // Scenario-comparison results carried into planning via "Use in plan"
  // (spec Phase 6 Sec.16) - frontend-only draft state, never persisted;
  // lives here (not in ChatPanel) so it survives across multiple Scenario
  // Comparison messages and is available the next time a plan is built.
  const [scenarioPlanInputs, setScenarioPlanInputs] = useState<ScenarioComparisonRef[]>([]);

  const [chatW, setChatW] = useState(CHAT_DEFAULT_CAP);
  const [inspectorW, setInspectorW] = useState(INSPECTOR_DEFAULT_CAP);
  const [chatVisible, setChatVisible] = useState(true);
  const [inspectorVisible, setInspectorVisible] = useState(true);
  const [inspectorTopH, setInspectorTopH] = useState(INSPECTOR_TOP_DEFAULT_H);
  const dragRef = useRef<{ mode: "chat" | "inspector"; startX: number; startVal: number } | null>(null);
  const rowDragRef = useRef<{ startY: number; startVal: number } | null>(null);

  function backendUnreachableMessage(err: unknown): string {
    return (
      `Could not reach the backend at ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}. ` +
      `Is it running? (${(err as Error).message})`
    );
  }

  // `focusIds`, when given, are the graph node ids of whatever was just
  // created/changed (memory approval, SUPERSEDE, decision creation, outcome
  // creation) - set together with the refreshed graph so IntelligenceGraph
  // re-frames only once the new nodes are actually present (spec Step 4).
  // Used by explicit user actions (reset button, chat mutations) - never
  // called from an effect, so it isn't (and shouldn't be) traced by
  // react-hooks/set-state-in-effect; see the mount effect below for that.
  const refresh = useCallback(async (focusIds?: string[]) => {
    try {
      const { graph, activity } = await loadDashboardData(CLIENT_ID);
      setGraph(graph);
      setActivity(activity);
      setLoadError(null);
      if (focusIds && focusIds.length > 0) {
        setFocusNodeIds(focusIds);
      }
    } catch (err) {
      setLoadError(backendUnreachableMessage(err));
    }
  }, []);

  // Initial load on mount. Deliberately NOT calling the `refresh` callback
  // above: react-hooks/set-state-in-effect's static analysis traces a
  // useCallback-produced function reference back to the setState calls in
  // its body and flags any effect that invokes it, regardless of the
  // await in between. An inline async closure defined and invoked directly
  // here isn't traced the same way (verified empirically), so this fetches
  // through the same shared `loadDashboardData` helper (no duplicated API
  // calls) but applies its own setState + unmount guard locally - which is
  // also the standard idiomatic shape for a mount-only fetch anyway.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { graph, activity } = await loadDashboardData(CLIENT_ID);
        if (!cancelled) {
          setGraph(graph);
          setActivity(activity);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(backendUnreachableMessage(err));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Initial panel widths from viewport (spec: "Never hardcode px only - the
  // center must remain the widest region at laptop widths"). Deferred via
  // rAF - a callback invoked *after* the effect runs, not the synchronous
  // effect body itself - which is the "calling setState in a callback"
  // shape react-hooks/set-state-in-effect expects, vs. the cascading-render
  // shape it flags for a bare setState call in the effect body.
  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      const w = window.innerWidth || 1600;
      setChatW(Math.max(CHAT_MIN, Math.round(Math.min(CHAT_DEFAULT_CAP, w * CHAT_DEFAULT_FRAC))));
      setInspectorW(Math.max(INSPECTOR_MIN, Math.round(Math.min(INSPECTOR_DEFAULT_CAP, w * INSPECTOR_DEFAULT_FRAC))));
    });
    return () => cancelAnimationFrame(raf);
  }, []);

  // Panel-divider drag (mousedown on either 1px separator).
  useEffect(() => {
    function onMove(e: MouseEvent) {
      const d = dragRef.current;
      if (!d) return;
      const delta = e.clientX - d.startX;
      if (d.mode === "chat") setChatW(Math.max(CHAT_MIN, Math.min(CHAT_MAX, d.startVal + delta)));
      else setInspectorW(Math.max(INSPECTOR_MIN, Math.min(INSPECTOR_MAX, d.startVal - delta)));
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
  }, []);

  function startChatResize(e: React.MouseEvent) {
    e.preventDefault();
    dragRef.current = { mode: "chat", startX: e.clientX, startVal: chatW };
  }
  function startInspectorResize(e: React.MouseEvent) {
    e.preventDefault();
    dragRef.current = { mode: "inspector", startX: e.clientX, startVal: inspectorW };
  }

  // Horizontal divider drag between the inspector's Context block and its
  // Activity feed below it - separate ref/effect from the column-width drag
  // above since it tracks clientY against a height, not clientX against a
  // width.
  useEffect(() => {
    function onMove(e: MouseEvent) {
      const d = rowDragRef.current;
      if (!d) return;
      setInspectorTopH(Math.max(INSPECTOR_TOP_MIN_H, Math.min(INSPECTOR_TOP_MAX_H, d.startVal + (e.clientY - d.startY))));
    }
    function onUp() {
      rowDragRef.current = null;
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  function startInspectorRowResize(e: React.MouseEvent) {
    e.preventDefault();
    rowDragRef.current = { startY: e.clientY, startVal: inspectorTopH };
  }

  // Default the inspector to the client node (Northwind) rather than an
  // empty panel on first load or right after a demo reset - computed at
  // render time (no effect/extra state needed) so it's correct immediately,
  // and never overrides an explicit click since selectedNode wins first.
  const defaultNode = graph?.nodes.find((n) => n.node_type === "client") ?? null;
  const displayedNode = selectedNode ?? defaultNode;
  const displayedId = selectedId ?? defaultNode?.id ?? null;

  function handleSelectNode(nodeId: string, node: GraphNodeData) {
    setSelectedId(nodeId);
    setSelectedNode(node);
  }

  function handleHighlight(ids: string[]) {
    setHighlightedIds(ids);
  }

  function handleReviewCampaign(campaignId: string) {
    setReviewCampaignRequest({ campaignId, nonce: Date.now() });
  }

  function handleGeneratePartnerBrief(partnerId: string) {
    setPartnerBriefRequest({ partnerId, nonce: Date.now() });
  }

  function handleViewHistory(subjectType: string, subjectId: string, predicate: string) {
    setMemoryHistoryRequest({ subjectType, subjectId, predicate, nonce: Date.now() });
  }

  function handleWhatChanged(subjectType: string, subjectId: string) {
    setWhatChangedRequest({ subjectType, subjectId, nonce: Date.now() });
  }

  function handleCompareScenarios(partnerId: string, currentAsk: number) {
    setScenarioComparisonRequest({ partnerId, currentAsk, nonce: Date.now() });
  }

  function handleBuildPlan(planningPeriod: string | undefined) {
    setPlanBuildRequest({ planningPeriod, nonce: Date.now() });
  }

  function handleUseInPlan(ref: ScenarioComparisonRef) {
    setScenarioPlanInputs((prev) => [...prev.filter((r) => r.partner_id !== ref.partner_id), ref]);
  }

  async function handleUpdatePlannedAction(actionId: string, patch: { status?: string; owner_id?: string | null; due_date?: string | null }) {
    // `status` here is always one of PLANNED_ACTION_STATUSES (the <select>
    // in MemoryInspector's PlannedActionSections is constrained to those
    // exact literal values) - cast rather than re-import the union just for
    // this call site.
    await api.updatePlannedAction(actionId, patch as Parameters<typeof api.updatePlannedAction>[1]);
    refresh([`planned_action:${actionId}`]);
  }

  function handleDemoReset() {
    // Force ChatPanel to fully remount (clearing its message/candidate/
    // decision/outcome state, which is local to that component and would
    // otherwise reference ids that no longer exist after a hard reset).
    setDemoEpoch((e) => e + 1);
    setSelectedNode(null);
    setSelectedId(null);
    setHighlightedIds([]);
    setFocusNodeIds([]);
    setReviewCampaignRequest(null);
    setPartnerBriefRequest(null);
    setMemoryHistoryRequest(null);
    setWhatChangedRequest(null);
    setScenarioComparisonRequest(null);
    setPlanBuildRequest(null);
    setScenarioPlanInputs([]);
    refresh();
  }

  if (loadError) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 32, background: SURFACE.app }}>
        <div style={{ maxWidth: 420, textAlign: "center", fontSize: 13, color: TEXT.secondary }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>⚠️</div>
          {loadError}
        </div>
      </div>
    );
  }

  const clientName = graph?.nodes.find((n) => n.node_type === "client")?.label ?? "";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden" }}>
      <header
        style={{
          flex: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 24,
          padding: "0 24px",
          height: 56,
          background: SURFACE.panel,
          borderBottom: `1px solid ${SURFACE.separator}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: ACCENT.green, flex: "none" }} />
          <span style={{ fontSize: 15, fontWeight: 600, color: TEXT.primary, whiteSpace: "nowrap" }}>AP Intelligence</span>
          <span style={{ width: 1, height: 16, background: "#1c2431", flex: "none" }} />
          <span style={{ fontSize: 14, color: TEXT.secondary, whiteSpace: "nowrap" }}>{headerContext(graph)}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flex: "none" }}>
          <span style={{ fontSize: 14, color: TEXT.strongSecondary2 }}>{clientName}</span>
          <div style={{ display: "flex", gap: 2 }}>
            <button
              onClick={() => setChatVisible((v) => !v)}
              title="Show/hide conversation panel"
              style={{ width: 26, height: 26, border: "none", background: "transparent", color: chatVisible ? TEXT.secondary : TEXT.faint2, fontSize: 13, cursor: "pointer" }}
            >
              ◧
            </button>
            <button
              onClick={() => setInspectorVisible((v) => !v)}
              title="Show/hide context panel"
              style={{ width: 26, height: 26, border: "none", background: "transparent", color: inspectorVisible ? TEXT.secondary : TEXT.faint2, fontSize: 13, cursor: "pointer" }}
            >
              ◨
            </button>
          </div>
          <ResetDemoButton onReset={handleDemoReset} />
        </div>
      </header>

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {chatVisible && (
          <>
            <section style={{ width: chatW, flex: "0 1 auto", minWidth: 240, display: "flex", flexDirection: "column", background: SURFACE.panel, minHeight: 0 }}>
              <ChatPanel
                key={demoEpoch}
                clientId={CLIENT_ID}
                graph={graph}
                onAfterMutation={refresh}
                onHighlight={handleHighlight}
                reviewCampaignRequest={reviewCampaignRequest}
                partnerBriefRequest={partnerBriefRequest}
                memoryHistoryRequest={memoryHistoryRequest}
                whatChangedRequest={whatChangedRequest}
                scenarioComparisonRequest={scenarioComparisonRequest}
                planBuildRequest={planBuildRequest}
                scenarioPlanInputs={scenarioPlanInputs}
                onUseInPlan={handleUseInPlan}
              />
            </section>
            <ResizeDivider direction="col" onMouseDown={startChatResize} />
          </>
        )}

        <section style={{ flex: 1, position: "relative", minWidth: 420 }}>
          {graph ? (
            <IntelligenceGraph graph={graph} highlightedIds={highlightedIds} focusNodeIds={focusNodeIds} selectedId={displayedId} onSelectNode={handleSelectNode} />
          ) : (
            <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: TEXT.faint }}>Loading graph…</div>
          )}
        </section>

        {inspectorVisible && (
          <>
            <ResizeDivider direction="col" onMouseDown={startInspectorResize} />
            <section style={{ width: inspectorW, flex: "0 1 auto", minWidth: 220, display: "flex", flexDirection: "column", background: SURFACE.panel, minHeight: 0 }}>
              <div style={{ flex: "none", height: inspectorTopH, minHeight: 0, overflow: "hidden" }}>
                <MemoryInspector
                  node={displayedNode}
                  graph={graph}
                  onReviewCampaign={handleReviewCampaign}
                  onGeneratePartnerBrief={handleGeneratePartnerBrief}
                  onViewHistory={handleViewHistory}
                  onWhatChanged={handleWhatChanged}
                  onCompareScenarios={handleCompareScenarios}
                  onBuildPlan={handleBuildPlan}
                  onUpdatePlannedAction={handleUpdatePlannedAction}
                />
              </div>
              <ResizeDivider direction="row" onMouseDown={startInspectorRowResize} />
              <ActivityFeed events={activity} />
            </section>
          </>
        )}
      </div>
    </div>
  );
}
