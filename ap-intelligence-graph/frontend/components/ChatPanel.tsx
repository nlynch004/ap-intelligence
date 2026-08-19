"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { ACCENT, FONT_MONO, SURFACE, TEXT } from "@/lib/design";
import type {
  CampaignReviewResponse,
  Decision,
  GraphResponse,
  MemoryCandidate,
  MemoryClaim,
  MemoryHistoryResponse,
  PartnerBriefResponse,
  PlanCreateResponse,
  PlanProposalResponse,
  ProposedPlannedAction,
  RecommendationResponse,
  ScenarioComparisonRef,
  ScenarioComparisonResponse,
  SimulateOutcomeResponse,
  WhatChangedSummary,
} from "@/lib/types";
import { CampaignReviewPanel } from "./CampaignReviewPanel";
import { CandidateMemoryReview } from "./CandidateMemoryReview";
import { ConflictDialog } from "./ConflictDialog";
import { MemoryHistoryPanel, WhatChangedPanel } from "./MemoryHistoryPanel";
import { PartnerBriefPanel } from "./PartnerBriefPanel";
import { PlanProposalPanel } from "./PlanProposalPanel";
import { RecommendationCard } from "./RecommendationCard";
import { ResizeDivider } from "./ResizeDivider";
import { ScenarioComparisonPanel } from "./ScenarioComparisonPanel";

type Msg =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string }
  | { id: string; role: "candidates"; candidates: MemoryCandidate[] }
  | { id: string; role: "recommendation"; recommendation: RecommendationResponse }
  | { id: string; role: "campaign_review"; review: CampaignReviewResponse }
  | { id: string; role: "partner_brief"; brief: PartnerBriefResponse }
  | { id: string; role: "memory_history"; history: MemoryHistoryResponse }
  | { id: string; role: "what_changed"; summary: WhatChangedSummary }
  | { id: string; role: "scenario_comparison"; comparison: ScenarioComparisonResponse }
  | { id: string; role: "plan_proposal"; proposal: PlanProposalResponse };

// The three-step "Creator renewal" workflow (design_handoff v2 Sec.2) maps
// 1:1 to this demo script's canned prompts - the same prompts previously
// offered as free-standing suggestion buttons. `stage` below is derived from
// real conversation/candidate/recommendation state, never persisted
// separately (spec "State Management": workflow state must remain a
// projection of real application state).
const STEP_DEFS = [
  {
    title: "Summit Sisters context",
    desc: "Retrieve current Summit Sisters context",
    // Deliberately partner-scoped in wording, not just "...on Northwind." -
    // the underlying query (active_client_memories) is still a broad,
    // unscoped pull of every active claim tied to this client, but since
    // Phase 1 added 4 more creators with no governed relationship memory of
    // their own (only campaign/evidence rows for the newer Campaign
    // Review/Partner Brief/Scenario Comparison workflows to use), Summit
    // Sisters remains the only partner-level belief that exists at a fresh
    // reset. Naming her here keeps the prompt honest about what the answer
    // will actually cover, rather than reading like a full-portfolio ask it
    // can't yet back up.
    prompt: "Bring me up to speed on Northwind's partnership with Summit Sisters.",
  },
  {
    title: "Strategy update",
    desc: "Capture what changed",
    prompt:
      "Northwind's strategy changed after last week's executive review. They now want to reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS is a little lower.",
  },
  { title: "Renewal decision", desc: "Evaluate Summit Sisters", prompt: "Summit Sisters wants $6,000 for another campaign. Should we renew them?" },
];

// Bounds for the draggable divider between the "Demo steps" block and
// "Chat conversation" below it.
const STEPS_DEFAULT_H = 240;
const STEPS_MIN_H = 130;
const STEPS_MAX_H = 460;

let uid = 0;
const nextId = () => `m${++uid}_${Date.now()}`;

export function ChatPanel({
  clientId,
  graph,
  onAfterMutation,
  onHighlight,
  reviewCampaignRequest,
  partnerBriefRequest,
  memoryHistoryRequest,
  whatChangedRequest,
  scenarioComparisonRequest,
  planBuildRequest,
  scenarioPlanInputs,
  onUseInPlan,
}: {
  clientId: string;
  graph: GraphResponse | null;
  /** focusIds, when given, are the graph node ids of whatever was just
   * created/changed - the parent re-frames the graph viewport around them. */
  onAfterMutation: (focusIds?: string[]) => void;
  onHighlight: (ids: string[]) => void;
  /** Set by the "Review campaign" button in MemoryInspector (via
   * LiveDemoView) - a distinct object each click (nonce) so the effect
   * below fires even for the same campaign twice in a row. The bounded
   * chat-text path ("Review Summit Sisters' May 2026 campaign.") reaches
   * the same backend pipeline through send() instead - this prop exists
   * only for the button, which already knows the exact campaign id and
   * has no reason to go through NLU month/partner matching. */
  reviewCampaignRequest?: { campaignId: string; nonce: number } | null;
  /** Same pattern as reviewCampaignRequest, for the "Generate partner
   * brief" button (Phase 3). The bounded chat-text path ("What should I
   * know before I speak with Summit Sisters?") reaches the same backend
   * pipeline through send() instead. */
  partnerBriefRequest?: { partnerId: string; nonce: number } | null;
  /** Same pattern, for the "View history" button on a MemoryClaim node
   * (Phase 4) - the claim already names its own subject_type/subject_id/
   * predicate, so the button skips NLU entirely. */
  memoryHistoryRequest?: { subjectType: string; subjectId: string; predicate: string; nonce: number } | null;
  /** Same pattern, for the "What changed?" button on a Client/Partner node. */
  whatChangedRequest?: { subjectType: string; subjectId: string; nonce: number } | null;
  /** Same pattern, for the "Compare scenarios" button on a Partner node
   * (Phase 5) - the button collects the current renewal ask inline before
   * firing this request, since the ask must never be invented. */
  scenarioComparisonRequest?: { partnerId: string; currentAsk: number; nonce: number } | null;
  /** Same pattern, for the "Build plan" button on the Client node (Phase 6). */
  planBuildRequest?: { planningPeriod: string | undefined; nonce: number } | null;
  /** Scenario-comparison results the user has carried into planning via
   * "Use in plan" (Phase 6 Sec.16) - frontend-only state, owned by
   * LiveDemoView so it survives across chat/button entry points and across
   * multiple Scenario Comparison messages, but never persisted. */
  scenarioPlanInputs?: ScenarioComparisonRef[];
  onUseInPlan?: (ref: ScenarioComparisonRef) => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [resolved, setResolved] = useState<Record<string, "approved" | "rejected" | "conflict">>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [activeConflict, setActiveConflict] = useState<{ candidate: MemoryCandidate; existingClaim: MemoryClaim } | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [outcomes, setOutcomes] = useState<Record<string, SimulateOutcomeResponse>>({});
  const [planCreations, setPlanCreations] = useState<Record<string, PlanCreateResponse>>({});
  const scrollRef = useRef<HTMLDivElement>(null);

  // Draggable horizontal divider between the "Demo steps" block and "Chat
  // conversation" below it - same mousedown/window-mousemove/mouseup
  // pattern as the vertical panel dividers in LiveDemoView.tsx.
  const [stepsH, setStepsH] = useState(STEPS_DEFAULT_H);
  const stepsDragRef = useRef<{ startY: number; startVal: number } | null>(null);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      const d = stepsDragRef.current;
      if (!d) return;
      setStepsH(Math.max(STEPS_MIN_H, Math.min(STEPS_MAX_H, d.startVal + (e.clientY - d.startY))));
    }
    function onUp() {
      stepsDragRef.current = null;
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  function startStepsResize(e: React.MouseEvent) {
    e.preventDefault();
    stepsDragRef.current = { startY: e.clientY, startVal: stepsH };
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, resolved, decisions, outcomes, planCreations]);

  // Derived workflow stage (0-3): how many of the three canned steps have
  // run their course. Never a separate source of truth - just a read of the
  // conversation transcript that's already state here.
  const stage = useMemo(() => {
    // campaign_review counts toward "an assistant reply happened" the same
    // way a plain assistant message does - it's an off-script query, not
    // one of the three canned steps, so it must not itself advance stage
    // past where the canned steps already are.
    const hasAssistantReply = messages.some((m) =>
      m.role === "assistant" || m.role === "campaign_review" || m.role === "partner_brief" ||
      m.role === "memory_history" || m.role === "what_changed" || m.role === "scenario_comparison" ||
      m.role === "plan_proposal",
    );
    const candidateMsgs = messages.filter((m): m is Extract<Msg, { role: "candidates" }> => m.role === "candidates");
    const hasCandidates = candidateMsgs.length > 0;
    const hasRecommendation = messages.some((m) => m.role === "recommendation");
    const candidatesAllResolved = hasCandidates && candidateMsgs.every((m) => m.candidates.every((c) => resolved[c.id] === "approved" || resolved[c.id] === "rejected"));

    let s = 0;
    if (hasAssistantReply || hasCandidates || hasRecommendation) s = 1;
    if (candidatesAllResolved) s = Math.max(s, 2);
    if (hasRecommendation) s = 3;
    return s;
  }, [messages, resolved]);

  function partnerName(partnerId: string): string {
    // Graph node ids are keyed by the backend's raw entity-table name
    // ("partner"), not the resolved display kind ("creator"/"publisher") -
    // see node_key() in app/routers/graph.py.
    const node = graph?.nodes.find((n) => n.id === `partner:${partnerId}`);
    return node?.label ?? partnerId.replace(/_/g, " ");
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setMessages((m) => [...m, { id: nextId(), role: "user", text: trimmed }]);
    setInput("");
    setSending(true);
    try {
      const resp = await api.sendChat(clientId, trimmed);
      if (resp.recommendation) {
        setMessages((m) => [...m, { id: nextId(), role: "recommendation", recommendation: resp.recommendation as RecommendationResponse }]);
        onHighlight(resp.recommendation.supporting_memory_ids);
      } else if (resp.campaign_review) {
        pushCampaignReview(resp.campaign_review);
      } else if (resp.partner_brief) {
        pushPartnerBrief(resp.partner_brief);
      } else if (resp.memory_history) {
        pushMemoryHistory(resp.memory_history);
      } else if (resp.what_changed) {
        pushWhatChanged(resp.what_changed);
      } else if (resp.scenario_comparison) {
        pushScenarioComparison(resp.scenario_comparison);
      } else if (resp.plan_proposal) {
        pushPlanProposal(resp.plan_proposal);
      } else if (resp.candidates.length > 0) {
        setMessages((m) => [...m, { id: nextId(), role: "candidates", candidates: resp.candidates }]);
      } else {
        setMessages((m) => [...m, { id: nextId(), role: "assistant", text: resp.reply }]);
        if (resp.referenced_memory_ids.length > 0) onHighlight(resp.referenced_memory_ids);
      }
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  function pushCampaignReview(review: CampaignReviewResponse) {
    setMessages((m) => [...m, { id: nextId(), role: "campaign_review", review }]);
    onHighlight([
      ...review.evidence.client_memory.map((c) => `memory_claim:${c.claim_id}`),
      ...review.evidence.partner_memory.map((c) => `memory_claim:${c.claim_id}`),
      ...review.evidence.measurement_cautions.map((c) => `memory_claim:${c.claim_id}`),
    ]);
  }

  // Driven by the "Review campaign" button (MemoryInspector, via
  // LiveDemoView) - calls the dedicated campaign-review endpoint directly
  // with the exact campaign id already known, rather than going through
  // send()'s NLU matching (that path exists for free-text chat instead -
  // see the module doc comment on reviewCampaignRequest above).
  async function reviewCampaignById(campaignId: string) {
    setMessages((m) => [...m, { id: nextId(), role: "user", text: "Review this campaign." }]);
    setSending(true);
    try {
      const review = await api.reviewCampaign(campaignId);
      pushCampaignReview(review);
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!reviewCampaignRequest) return;
    reviewCampaignById(reviewCampaignRequest.campaignId);
    // Only re-run when a new request comes in (nonce changes) - not on
    // every render, which reviewCampaignById's own identity would trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewCampaignRequest]);

  function pushPartnerBrief(brief: PartnerBriefResponse) {
    setMessages((m) => [...m, { id: nextId(), role: "partner_brief", brief }]);
    onHighlight([
      ...brief.evidence.relationship_history.map((c) => `memory_claim:${c.claim_id}`),
      ...brief.evidence.client_context.map((c) => `memory_claim:${c.claim_id}`),
      ...brief.evidence.measurement_cautions.map((c) => `memory_claim:${c.claim_id}`),
      ...brief.evidence.campaigns.map((c) => `campaign:${c.campaign_id}`),
      ...brief.evidence.prior_decisions.map((d) => `decision:${d.decision_id}`),
      ...brief.evidence.outcomes.map((o) => `outcome:${o.outcome_id}`),
    ]);
  }

  // Driven by the "Generate partner brief" button (MemoryInspector, via
  // LiveDemoView) - same rationale as reviewCampaignById above: the exact
  // partner id is already known, no need to go through send()'s NLU path.
  async function generatePartnerBriefById(partnerId: string) {
    setMessages((m) => [...m, { id: nextId(), role: "user", text: "Generate a partner brief." }]);
    setSending(true);
    try {
      const brief = await api.getPartnerBrief(partnerId, clientId);
      pushPartnerBrief(brief);
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!partnerBriefRequest) return;
    generatePartnerBriefById(partnerBriefRequest.partnerId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [partnerBriefRequest]);

  function pushMemoryHistory(history: MemoryHistoryResponse) {
    setMessages((m) => [...m, { id: nextId(), role: "memory_history", history }]);
    onHighlight(history.timeline.changes.map((c) => `memory_claim:${c.claim_id}`));
  }

  // Driven by the "View history" button on a MemoryClaim node (Phase 4) -
  // the claim already names its own subject_type/subject_id/predicate.
  async function viewHistoryById(subjectType: string, subjectId: string, predicate: string) {
    setMessages((m) => [...m, { id: nextId(), role: "user", text: "View history." }]);
    setSending(true);
    try {
      const history = await api.getMemoryHistory(subjectType, subjectId, predicate, clientId);
      pushMemoryHistory(history);
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!memoryHistoryRequest) return;
    viewHistoryById(memoryHistoryRequest.subjectType, memoryHistoryRequest.subjectId, memoryHistoryRequest.predicate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memoryHistoryRequest]);

  function pushWhatChanged(summary: WhatChangedSummary) {
    setMessages((m) => [...m, { id: nextId(), role: "what_changed", summary }]);
  }

  // Driven by the "What changed?" button on a Client/Partner node (Phase 4).
  async function whatChangedById(subjectType: string, subjectId: string) {
    setMessages((m) => [...m, { id: nextId(), role: "user", text: "What changed?" }]);
    setSending(true);
    try {
      const summary = await api.getWhatChanged(subjectType, subjectId, clientId);
      pushWhatChanged(summary);
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!whatChangedRequest) return;
    whatChangedById(whatChangedRequest.subjectType, whatChangedRequest.subjectId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [whatChangedRequest]);

  function pushScenarioComparison(comparison: ScenarioComparisonResponse) {
    setMessages((m) => [...m, { id: nextId(), role: "scenario_comparison", comparison }]);
    onHighlight([
      ...comparison.evidence.campaigns.map((c) => `campaign:${c.campaign_id}`),
      ...comparison.evidence.client_context.map((c) => `memory_claim:${c.claim_id}`),
      ...comparison.evidence.partner_memory.map((c) => `memory_claim:${c.claim_id}`),
      ...comparison.evidence.measurement_cautions.map((c) => `memory_claim:${c.claim_id}`),
      ...comparison.evidence.prior_decisions.map((d) => `decision:${d.decision_id}`),
      ...comparison.evidence.outcomes.map((o) => `outcome:${o.outcome_id}`),
    ]);
  }

  // Driven by the "Compare scenarios" button (MemoryInspector, via
  // LiveDemoView) - the button already collected the current renewal ask
  // inline, so this skips send()'s NLU/dollar-amount parsing entirely.
  async function compareScenariosById(partnerId: string, currentAsk: number) {
    setMessages((m) => [...m, { id: nextId(), role: "user", text: `Compare renewal scenarios (current ask $${currentAsk.toLocaleString()}).` }]);
    setSending(true);
    try {
      const comparison = await api.compareScenarios(partnerId, clientId, currentAsk);
      pushScenarioComparison(comparison);
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!scenarioComparisonRequest) return;
    compareScenariosById(scenarioComparisonRequest.partnerId, scenarioComparisonRequest.currentAsk);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioComparisonRequest]);

  function pushPlanProposal(proposal: PlanProposalResponse) {
    setMessages((m) => [...m, { id: nextId(), role: "plan_proposal", proposal }]);
    onHighlight([
      ...proposal.context.partners.flatMap((p) => p.campaigns.map((c) => `campaign:${c.campaign_id}`)),
      ...proposal.context.partners.flatMap((p) => p.measurement_cautions.map((c) => `memory_claim:${c.claim_id}`)),
      ...proposal.context.partners.flatMap((p) => p.partner_memory.map((c) => `memory_claim:${c.claim_id}`)),
      ...proposal.context.client.current_strategy.map((c) => `memory_claim:${c.claim_id}`),
    ]);
  }

  // Driven by the "Build plan" button (MemoryInspector, via LiveDemoView) -
  // client-level, so unlike the other by-id helpers this needs no entity id
  // beyond clientId, which the panel already has.
  async function buildPlanById(planningPeriod: string | undefined) {
    setMessages((m) => [...m, { id: nextId(), role: "user", text: planningPeriod ? `Build Northwind's ${planningPeriod} creator plan.` : "Build Northwind's next creator plan." }]);
    setSending(true);
    try {
      const proposal = await api.proposePlan(clientId, { planningPeriod, scenarioInputs: scenarioPlanInputs });
      pushPlanProposal(proposal);
    } catch (err) {
      setMessages((m) => [...m, { id: nextId(), role: "assistant", text: `Something went wrong: ${(err as Error).message}` }]);
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    if (!planBuildRequest) return;
    buildPlanById(planBuildRequest.planningPeriod);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planBuildRequest]);

  // Persists only the actions the human approved (spec Phase 6 Sec.14 step
  // 3) - the proposal itself (msgId's PlanProposalResponse) never wrote
  // anything; this is the one call in the whole planning flow that does.
  async function createPlanFromApproved(msgId: string, proposal: PlanProposalResponse, approved: ProposedPlannedAction[]) {
    setBusyId(msgId);
    try {
      const created = await api.createPlan({
        client_id: proposal.client_id,
        name: proposal.plan_name,
        planning_period: proposal.planning_period,
        objective: proposal.objective,
        actions: approved.map((a) => ({
          partner_id: a.partner_id,
          action_type: a.action_type,
          summary: a.summary,
          rationale: a.rationale,
          supporting_memory_ids: a.supporting_memory_ids,
          supporting_campaign_ids: a.supporting_campaign_ids,
          source_scenario_id: a.source_scenario_id,
        })),
      });
      setPlanCreations((p) => ({ ...p, [msgId]: created }));
      onAfterMutation([`plan:${created.plan.id}`, ...created.plan.actions.map((a) => `planned_action:${a.id}`)]);
    } finally {
      setBusyId(null);
    }
  }

  async function approve(c: MemoryCandidate) {
    setBusyId(c.id);
    try {
      const resp = await api.reviewMemory(c.id, "approve");
      if (resp.requires_conflict_resolution && resp.conflict_with_claim) {
        setResolved((r) => ({ ...r, [c.id]: "conflict" }));
        setActiveConflict({ candidate: c, existingClaim: resp.conflict_with_claim });
      } else {
        setResolved((r) => ({ ...r, [c.id]: "approved" }));
        onAfterMutation(resp.claim ? [`memory_claim:${resp.claim.id}`] : undefined);
      }
    } finally {
      setBusyId(null);
    }
  }

  async function reject(c: MemoryCandidate) {
    setBusyId(c.id);
    try {
      await api.reviewMemory(c.id, "reject");
      setResolved((r) => ({ ...r, [c.id]: "rejected" }));
      onAfterMutation();
    } finally {
      setBusyId(null);
    }
  }

  async function approveAll(candidates: MemoryCandidate[]) {
    for (const c of candidates) {
      if (!resolved[c.id]) {
        await approve(c);
      }
    }
  }

  async function resolveConflict(operation: "SUPERSEDE" | "REJECT") {
    if (!activeConflict) return;
    setBusyId(activeConflict.candidate.id);
    try {
      const resp = await api.resolveConflict(activeConflict.candidate.id, operation);
      setResolved((r) => ({ ...r, [activeConflict.candidate.id]: operation === "SUPERSEDE" ? "approved" : "rejected" }));
      setActiveConflict(null);
      // Focus both the new active claim and the now-superseded one, so the
      // supersession is visually legible (old node dimmed, new one active).
      const focusIds = [resp.new_claim, resp.superseded_claim]
        .filter((c): c is NonNullable<typeof c> => c != null)
        .map((c) => `memory_claim:${c.id}`);
      onAfterMutation(focusIds.length > 0 ? focusIds : undefined);
    } finally {
      setBusyId(null);
    }
  }

  async function acceptRecommendation(msgId: string, rec: RecommendationResponse) {
    setBusyId(msgId);
    try {
      const decision = await api.createDecision({
        client_id: rec.client_id,
        partner_id: rec.partner_id,
        summary: `Renew ${partnerName(rec.partner_id)} under ${rec.recommendation.replace(/_/g, " ")}`,
        terms: rec.recommended_terms,
        rationale: rec.explanation,
        motivated_by_claim_ids: rec.supporting_memory_ids,
      });
      setDecisions((d) => ({ ...d, [msgId]: decision }));
      onAfterMutation([`decision:${decision.id}`]);
    } finally {
      setBusyId(null);
    }
  }

  async function simulateOutcome(msgId: string, decision: Decision) {
    setBusyId(msgId);
    try {
      const resp = await api.simulateOutcome(decision.id);
      setOutcomes((o) => ({ ...o, [msgId]: resp }));
      const focusIds = [`outcome:${resp.outcome.id}`];
      if (resp.pattern_id) focusIds.push(`portfolio_pattern:${resp.pattern_id}`);
      onAfterMutation(focusIds);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div className="ap-scroll" style={{ flex: "none", height: stepsH, overflowY: "auto", padding: "22px 22px 16px" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 14 }}>DEMO STEPS</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {STEP_DEFS.map((step, i) => {
            const done = stage > i;
            const current = stage === i;
            const clickable = i <= stage && !sending;
            const statusText = done ? "✓ Complete" : current ? "● Current" : "○ Next";
            const statusColor = done ? ACCENT.green : current ? ACCENT.blue : TEXT.faint2;
            const titleColor = current ? TEXT.primary : done ? TEXT.strongSecondary2 : TEXT.secondary2;
            return (
              <button
                key={step.title}
                onClick={() => clickable && send(step.prompt)}
                disabled={!clickable}
                style={{
                  display: "flex",
                  gap: 14,
                  textAlign: "left",
                  background: current ? SURFACE.activeRow : "transparent",
                  border: "none",
                  borderRadius: 8,
                  padding: "11px 12px",
                  cursor: clickable ? "pointer" : "default",
                  width: "100%",
                }}
              >
                <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: TEXT.faint2, paddingTop: 2, flex: "none" }}>{String(i + 1).padStart(2, "0")}</span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <span style={{ display: "block", fontSize: 14, fontWeight: 600, color: titleColor }}>{step.title}</span>
                  <span style={{ display: "block", fontSize: 13, color: TEXT.metadata, marginTop: 1 }}>{step.desc}</span>
                </span>
                <span style={{ fontSize: 12, color: statusColor, flex: "none", paddingTop: 3, whiteSpace: "nowrap" }}>{statusText}</span>
              </button>
            );
          })}
        </div>
      </div>

      <ResizeDivider direction="row" onMouseDown={startStepsResize} />

      <div style={{ flex: "none", padding: "14px 22px 6px" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint }}>CHAT CONVERSATION</div>
      </div>

      <div ref={scrollRef} className="ap-scroll" style={{ flex: 1, overflowY: "auto", padding: "6px 22px 22px", display: "flex", flexDirection: "column", gap: 14, minHeight: 0 }}>
        {messages.length === 0 && <div style={{ fontSize: 13, color: TEXT.faint, fontStyle: "italic" }}>Use the steps above, or ask a question below.</div>}

        {messages.map((m) => {
          if (m.role === "user") {
            return (
              <div key={m.id} style={{ display: "flex", justifyContent: "flex-end" }}>
                <div style={{ maxWidth: "88%", borderRadius: 12, padding: "10px 14px", fontSize: 14, lineHeight: 1.55, whiteSpace: "pre-line", background: "#18222f", color: TEXT.primary, animation: "fadeup 0.25s ease" }}>
                  {m.text}
                </div>
              </div>
            );
          }
          if (m.role === "assistant") {
            return (
              <div key={m.id} style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{ maxWidth: "100%", fontSize: 14, lineHeight: 1.55, whiteSpace: "pre-line", color: "#b3c0d3", animation: "fadeup 0.25s ease" }}>{m.text}</div>
              </div>
            );
          }
          if (m.role === "candidates") {
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <CandidateMemoryReview
                  candidates={m.candidates}
                  resolved={resolved}
                  busyId={busyId}
                  onApprove={approve}
                  onReject={reject}
                  onApproveAll={() => approveAll(m.candidates)}
                />
              </div>
            );
          }
          if (m.role === "campaign_review") {
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 18 }}>
                  <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 16 }}>CAMPAIGN REVIEW</div>
                  <CampaignReviewPanel
                    evidence={m.review.evidence}
                    summary={m.review.summary}
                    whatWorked={m.review.what_worked}
                    whatIsUncertain={m.review.what_is_uncertain}
                    planningImplications={m.review.planning_implications}
                  />
                </div>
                {m.review.candidate_lessons.length > 0 && (
                  <div style={{ marginTop: 14 }}>
                    <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 10 }}>CANDIDATE LESSONS</div>
                    <CandidateMemoryReview
                      candidates={m.review.candidate_lessons}
                      resolved={resolved}
                      busyId={busyId}
                      onApprove={approve}
                      onReject={reject}
                      onApproveAll={() => approveAll(m.review.candidate_lessons)}
                    />
                  </div>
                )}
              </div>
            );
          }
          if (m.role === "partner_brief") {
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 18 }}>
                  <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 16 }}>PARTNER BRIEF</div>
                  <PartnerBriefPanel evidence={m.brief.evidence} onHighlight={onHighlight} />

                  <div style={{ borderTop: `1px solid ${SURFACE.separatorInner2}`, paddingTop: 16 }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 10 }}>
                      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint }}>CONVERSATION PREP</div>
                      <span style={{ fontSize: 10.5, letterSpacing: "0.06em", color: ACCENT.purple, fontFamily: FONT_MONO }}>MODEL SYNTHESIS</span>
                    </div>
                    <div style={{ fontSize: 14, lineHeight: 1.55, color: TEXT.primary, marginBottom: 4 }}>{m.brief.relationship_summary}</div>
                    <div style={{ fontSize: 14, lineHeight: 1.55, color: TEXT.secondary2, marginBottom: 14 }}>{m.brief.performance_summary}</div>

                    <div style={{ fontSize: 12.5, color: TEXT.metadata, marginBottom: 6 }}>What to know</div>
                    <ul style={{ margin: "0 0 14px", paddingLeft: 18, display: "flex", flexDirection: "column", gap: 5 }}>
                      {m.brief.what_to_know.map((s, i) => (
                        <li key={i} style={{ fontSize: 13.5, lineHeight: 1.5, color: TEXT.secondary2 }}>{s}</li>
                      ))}
                    </ul>

                    {m.brief.negotiation_considerations.length > 0 && (
                      <>
                        <div style={{ fontSize: 12.5, color: TEXT.metadata, marginBottom: 6 }}>Negotiation considerations</div>
                        <ul style={{ margin: "0 0 14px", paddingLeft: 18, display: "flex", flexDirection: "column", gap: 5 }}>
                          {m.brief.negotiation_considerations.map((s, i) => (
                            <li key={i} style={{ fontSize: 13.5, lineHeight: 1.5, color: TEXT.secondary2 }}>{s}</li>
                          ))}
                        </ul>
                      </>
                    )}

                    {m.brief.open_questions.length > 0 && (
                      <>
                        <div style={{ fontSize: 12.5, color: ACCENT.amber, marginBottom: 6 }}>Open questions</div>
                        <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 5 }}>
                          {m.brief.open_questions.map((s, i) => (
                            <li key={i} style={{ fontSize: 13.5, lineHeight: 1.5, color: "#d2a468" }}>{s}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          }
          if (m.role === "memory_history") {
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 18 }}>
                  <MemoryHistoryPanel history={m.history} onHighlight={onHighlight} />
                </div>
              </div>
            );
          }
          if (m.role === "what_changed") {
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 18 }}>
                  <WhatChangedPanel summary={m.summary} onHighlight={onHighlight} />
                </div>
              </div>
            );
          }
          if (m.role === "scenario_comparison") {
            const partnerId = m.comparison.evidence.partner.partner_id;
            const usedInPlan = (scenarioPlanInputs ?? []).some((r) => r.partner_id === partnerId);
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 18 }}>
                  <ScenarioComparisonPanel
                    evidence={m.comparison.evidence}
                    preferredScenarioId={m.comparison.preferred_scenario_id}
                    comparisonSummary={m.comparison.comparison_summary}
                    tradeoffs={m.comparison.tradeoffs}
                    uncertainties={m.comparison.uncertainties}
                    questionsBeforeFinalizing={m.comparison.questions_before_finalizing}
                    confidence={m.comparison.confidence}
                    onHighlight={onHighlight}
                    onUseInPlan={
                      onUseInPlan
                        ? () =>
                            onUseInPlan({
                              partner_id: partnerId,
                              preferred_scenario_id: m.comparison.preferred_scenario_id,
                              comparison_summary: m.comparison.comparison_summary,
                              scenarios: m.comparison.evidence.scenarios,
                            })
                        : undefined
                    }
                    usedInPlan={usedInPlan}
                  />
                </div>
              </div>
            );
          }
          if (m.role === "plan_proposal") {
            return (
              <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
                <div style={{ background: SURFACE.raised, borderRadius: 12, padding: 18 }}>
                  <PlanProposalPanel
                    proposal={m.proposal}
                    createdPlan={planCreations[m.id] ?? null}
                    busy={busyId === m.id}
                    onCreatePlan={(approved) => createPlanFromApproved(m.id, m.proposal, approved)}
                  />
                </div>
              </div>
            );
          }
          return (
            <div key={m.id} style={{ animation: "fadeup 0.3s ease" }}>
              <RecommendationCard
                recommendation={m.recommendation}
                decision={decisions[m.id] ?? null}
                outcomeResp={outcomes[m.id] ?? null}
                busy={busyId === m.id}
                onAccept={() => acceptRecommendation(m.id, m.recommendation)}
                onSimulate={() => decisions[m.id] && simulateOutcome(m.id, decisions[m.id])}
              />
            </div>
          );
        })}

        {sending && <div style={{ fontSize: 13, color: TEXT.faint, fontStyle: "italic" }}>thinking…</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        style={{ borderTop: `1px solid ${SURFACE.separatorInner}`, padding: 12, display: "flex", gap: 8 }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tell the agent something, or ask a question…"
          style={{ flex: 1, fontSize: 13, borderRadius: 8, border: `1px solid ${SURFACE.separator}`, background: SURFACE.raised, color: TEXT.primary, padding: "9px 12px", outline: "none" }}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          style={{ fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8, border: "none", background: "#18222f", color: TEXT.primary, cursor: "pointer", opacity: sending || !input.trim() ? 0.4 : 1 }}
        >
          Send
        </button>
      </form>

      {activeConflict && (
        <ConflictDialog
          candidate={activeConflict.candidate}
          existingClaim={activeConflict.existingClaim}
          busy={busyId === activeConflict.candidate.id}
          onResolve={resolveConflict}
          onDismiss={() => setActiveConflict(null)}
        />
      )}
    </div>
  );
}
