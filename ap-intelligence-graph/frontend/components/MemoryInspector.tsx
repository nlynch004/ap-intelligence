"use client";

import { useState } from "react";
import { ACCENT, FAMILIES, FONT_MONO, TEXT, predicateLabel, sentenceCase, titleCase } from "@/lib/design";
import { describeNode } from "@/lib/nodeVisuals";
import type { GraphNodeData, GraphResponse } from "@/lib/types";

function fmtVal(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return v.toLocaleString();
  return String(v).replace(/_/g, " ");
}

function fmtMoney(v: unknown): string {
  return typeof v === "number" ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : fmtVal(v);
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 26 }}>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 12 }}>{label}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>{children}</div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 13, color: TEXT.metadata }}>{label}</div>
      <div style={{ fontSize: 14.5, color: TEXT.strongSecondary, marginTop: 2, fontFamily: mono ? FONT_MONO : "inherit" }}>{value}</div>
    </div>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return <div style={{ marginTop: 24, fontSize: 13.5, lineHeight: 1.6, color: TEXT.secondary2 }}>{children}</div>;
}

function rawId(node: GraphNodeData): string {
  return node.id.split(":").slice(1).join(":");
}

function findClaimByRawId(graph: GraphResponse | null | undefined, id: unknown): GraphNodeData | undefined {
  if (typeof id !== "string") return undefined;
  return graph?.nodes.find((n) => n.node_type === "memory_claim" && n.id === `memory_claim:${id}`);
}

function WhatChangedButton({ node, onWhatChanged }: { node: GraphNodeData; onWhatChanged?: (subjectType: string, subjectId: string) => void }) {
  if (!onWhatChanged) return null;
  const subjectType = node.node_type === "client" ? "client" : node.node_type; // creator | publisher already match subject_type
  return (
    <button
      onClick={() => onWhatChanged(subjectType, rawId(node))}
      style={{
        marginTop: 26, fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8,
        border: `1px solid ${ACCENT.blue}`, background: "transparent", color: ACCENT.blue, cursor: "pointer",
      }}
    >
      What changed?
    </button>
  );
}

function ClientSections({
  node, graph, onWhatChanged, onBuildPlan, planBuildBusy,
}: {
  node: GraphNodeData;
  graph: GraphResponse | null;
  onWhatChanged?: (subjectType: string, subjectId: string) => void;
  onBuildPlan?: (planningPeriod: string | undefined) => void;
  planBuildBusy?: boolean;
}) {
  const d = node.data ?? {};
  const clientRaw = rawId(node);
  const campaignCount = graph ? graph.edges.filter((e) => e.source === node.id && e.relationship === "HAS_CAMPAIGN").length : 0;

  const activeClaims = (graph?.nodes ?? []).filter(
    (n) => n.node_type === "memory_claim" && n.status === "active" && n.data.subject_type === "client" && n.data.subject_id === clientRaw,
  );
  const byPredicate = (p: string) => activeClaims.find((c) => c.data.predicate === p);
  const strategy = byPredicate("partnership_strategy");
  const objective = byPredicate("primary_growth_objective");
  const tradeoff = byPredicate("accepts_tradeoff");

  const relatedPartners = (graph?.nodes ?? []).filter(
    (n) => (n.node_type === "creator" || n.node_type === "publisher") && graph?.edges.some((e) => e.source === node.id && e.target === n.id),
  );
  const relatedTeam = (graph?.nodes ?? []).filter(
    (n) => n.node_type === "team_member" && graph?.edges.some((e) => e.source === n.id && e.target === node.id && e.relationship === "MANAGES"),
  );
  const plans = (graph?.nodes ?? []).filter(
    (n) => n.node_type === "plan" && graph?.edges.some((e) => e.source === node.id && e.target === n.id && e.relationship === "HAS_PLAN"),
  );

  return (
    <>
      <Section label="OVERVIEW">
        <Row label="Industry" value={fmtVal(d.industry)} />
        <Row label="Open campaigns" value={campaignCount} />
      </Section>
      {(strategy || objective || tradeoff) && (
        <Section label="CURRENT STRATEGY">
          {strategy && <Row label={predicateLabel("partnership_strategy")} value={sentenceCase(strategy.data.value as string)} />}
          {objective && <Row label={predicateLabel("primary_growth_objective")} value={sentenceCase(objective.data.value as string)} />}
          {tradeoff && <Row label={predicateLabel("accepts_tradeoff")} value={sentenceCase(tradeoff.data.value as string)} />}
        </Section>
      )}
      {(relatedPartners.length > 0 || relatedTeam.length > 0) && (
        <Section label="RELATED">
          {relatedPartners.map((p) => (
            <Row key={p.id} label={p.label} value={titleCase(p.node_type)} />
          ))}
          {relatedTeam.map((m) => (
            <Row key={m.id} label={m.label} value={fmtVal(m.data.role) === "—" ? "Team member" : fmtVal(m.data.role)} />
          ))}
        </Section>
      )}
      {plans.length > 0 && (
        <Section label="PLANS">
          {plans.map((p) => (
            <Row key={p.id} label={p.label} value={`${titleCase(p.status ?? "")} · ${fmtVal(p.data.action_count)} action(s)`} />
          ))}
        </Section>
      )}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <WhatChangedButton node={node} onWhatChanged={onWhatChanged} />
        <BuildPlanControl onBuildPlan={onBuildPlan} busy={planBuildBusy} />
      </div>
    </>
  );
}

/** Client-level "Build plan" entry point (spec Phase 6 Sec.15: "Prefer
 * client-level entry because a Plan spans multiple partners"). Collapsed
 * behind a button, same pattern as CompareScenariosControl below, revealing
 * an optional planning-period field ("Q4", left blank for "next"). */
function BuildPlanControl({ onBuildPlan, busy }: { onBuildPlan?: (planningPeriod: string | undefined) => void; busy?: boolean }) {
  const [open, setOpen] = useState(false);
  const [period, setPeriod] = useState("");
  if (!onBuildPlan) return null;

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          marginTop: 12, fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8,
          border: "none", background: ACCENT.blue, color: "#0a1622", cursor: "pointer",
        }}
      >
        Build plan
      </button>
    );
  }

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 12, color: TEXT.metadata, marginBottom: 6 }}>Planning period (optional)</div>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          placeholder="Q4"
          autoFocus
          style={{ flex: 1, fontSize: 13, borderRadius: 8, border: `1px solid ${SURFACE_SEPARATOR}`, background: "transparent", color: TEXT.primary, padding: "8px 10px", outline: "none" }}
        />
        <button
          disabled={busy}
          onClick={() => onBuildPlan(period.trim() || undefined)}
          style={{ fontSize: 13, fontWeight: 600, padding: "8px 14px", borderRadius: 8, border: "none", background: ACCENT.blue, color: "#0a1622", cursor: "pointer", opacity: busy ? 0.6 : 1 }}
        >
          Build
        </button>
      </div>
    </div>
  );
}

function HistoryButton({ node, onViewHistory }: { node: GraphNodeData; onViewHistory?: (subjectType: string, subjectId: string, predicate: string) => void }) {
  const d = node.data ?? {};
  if (!onViewHistory || typeof d.subject_type !== "string" || typeof d.subject_id !== "string" || typeof d.predicate !== "string") return null;
  return (
    <button
      onClick={() => onViewHistory(d.subject_type as string, d.subject_id as string, d.predicate as string)}
      style={{
        marginTop: 8, fontSize: 12.5, fontWeight: 600, padding: "7px 14px", borderRadius: 8,
        border: `1px solid ${ACCENT.blue}`, background: "transparent", color: ACCENT.blue, cursor: "pointer",
      }}
    >
      View history
    </button>
  );
}

function MemoryClaimSections({ node, graph, onViewHistory }: { node: GraphNodeData; graph: GraphResponse | null; onViewHistory?: (subjectType: string, subjectId: string, predicate: string) => void }) {
  const d = node.data ?? {};
  const status = node.status;
  const claimClass = d.claim_class as string | undefined;
  const historical = status === "superseded" || status === "expired" || status === "deprecated";
  const isHypothesis = claimClass === "hypothesis" || status === "needs_review";
  const source = (d.source ?? {}) as Record<string, unknown>;

  const supersedesLabels = (Array.isArray(d.supersedes) ? (d.supersedes as string[]) : []).map((id) => {
    const c = findClaimByRawId(graph, id);
    return c ? sentenceCase(c.data.value as string) : id;
  });
  const supersededByLabel = (() => {
    const c = findClaimByRawId(graph, d.superseded_by);
    return c ? sentenceCase(c.data.value as string) : fmtVal(d.superseded_by);
  })();

  if (historical) {
    return (
      <>
        <Section label="VALIDITY">
          <Row label="Effective" value={`${fmtVal(d.valid_from)} → ${d.valid_to ? fmtVal(d.valid_to) : "—"}`} />
        </Section>
        {Boolean(d.superseded_by) && (
          <Section label="HISTORY">
            <Row label="Superseded by" value={supersededByLabel} />
          </Section>
        )}
        <Section label="SYSTEM">
          <Row label="Status" value={fmtVal(status)} mono />
          <Row label="Confidence at retirement" value={typeof d.confidence === "number" ? d.confidence.toFixed(2) : "—"} mono />
        </Section>
        <Note>Excluded from retrieval but preserved for audit. The system changed its mind without forgetting its history.</Note>
        <HistoryButton node={node} onViewHistory={onViewHistory} />
      </>
    );
  }

  if (isHypothesis) {
    return (
      <>
        <Section label="SOURCE">
          {Boolean(source.type) && <Row label="Origin" value={fmtVal(source.type)} />}
          {Boolean(source.speaker) && <Row label="Speaker" value={fmtVal(source.speaker)} />}
        </Section>
        <Section label="SYSTEM">
          <Row label="Claim class" value={fmtVal(claimClass)} mono />
          <Row label="Status" value={fmtVal(status)} mono />
          <Row label="Confidence" value={typeof d.confidence === "number" ? d.confidence.toFixed(2) : "—"} mono />
        </Section>
        <Note>Unverified hypothesis, not a confirmed fact. Requires human review before it is treated as ground truth.</Note>
        <HistoryButton node={node} onViewHistory={onViewHistory} />
      </>
    );
  }

  return (
    <>
      <Section label="SOURCE">
        {Boolean(source.type) && <Row label="Origin" value={fmtVal(source.type)} />}
        {Boolean(source.speaker) && <Row label="Speaker" value={fmtVal(source.speaker)} />}
      </Section>
      <Section label="VALIDITY">
        <Row label="Effective" value={`${fmtVal(d.valid_from)} → ${d.valid_to ? fmtVal(d.valid_to) : "Present"}`} />
      </Section>
      {supersedesLabels.length > 0 && (
        <Section label="HISTORY">
          <Row label="Supersedes" value={supersedesLabels.join(", ")} />
        </Section>
      )}
      <Section label="SYSTEM">
        <Row label="Claim class" value={fmtVal(claimClass)} mono />
        <Row label="Confidence" value={typeof d.confidence === "number" ? d.confidence.toFixed(2) : "—"} mono />
        <Row label="Authority" value={typeof d.authority_score === "number" ? d.authority_score.toFixed(2) : "—"} mono />
      </Section>
      <HistoryButton node={node} onViewHistory={onViewHistory} />
    </>
  );
}

function CampaignSections({ node, onReviewCampaign, busy }: { node: GraphNodeData; onReviewCampaign?: (campaignId: string) => void; busy?: boolean }) {
  const d = node.data ?? {};
  const fee = d.flat_fee as number | undefined;
  const revenue = d.attributed_revenue as number | undefined;
  const roas = fee && revenue != null ? (revenue / fee).toFixed(2) + "x" : "—";
  return (
    <>
      <Section label="COMMERCIALS">
        <Row label="Flat fee" value={fmtMoney(d.flat_fee)} />
        <Row label="Attributed revenue" value={fmtMoney(d.attributed_revenue)} />
        <Row label="ROAS" value={roas} mono />
      </Section>
      <Section label="MEASUREMENT">
        <Row label="Link clicks" value={fmtVal(d.link_clicks)} mono />
        <Row label="Code redemptions" value={fmtVal(d.code_redemptions)} mono />
      </Section>
      {onReviewCampaign && (
        <button
          disabled={busy}
          onClick={() => onReviewCampaign(rawId(node))}
          style={{
            marginTop: 26, fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8,
            border: "none", background: ACCENT.blue, color: "#0a1622", cursor: "pointer", opacity: busy ? 0.6 : 1,
          }}
        >
          Review campaign
        </button>
      )}
    </>
  );
}

function DecisionSections({ node, graph }: { node: GraphNodeData; graph: GraphResponse | null }) {
  const d = node.data ?? {};
  const terms = (d.terms ?? {}) as Record<string, unknown>;
  const motivated = (graph?.nodes ?? []).filter(
    (n) => graph?.edges.some((e) => e.source === node.id && e.target === n.id && e.relationship === "MOTIVATED_BY"),
  );
  return (
    <>
      <Section label="TERMS">
        <Row label="Base fee" value={fmtMoney(terms.base_fee)} />
        <Row label="Performance bonus" value={terms.performance_bonus_pct != null ? `${terms.performance_bonus_pct}%` : "—"} />
        <Row label="Bonus basis" value={fmtVal(terms.bonus_basis)} />
      </Section>
      {motivated.length > 0 && (
        <Section label="MOTIVATED BY">
          {motivated.map((m) => (
            <Row key={m.id} label={describeNode(m, graph).typeLabel} value={m.node_type === "portfolio_pattern" ? m.label : sentenceCase(m.data.value as string)} />
          ))}
        </Section>
      )}
      {Boolean(d.rationale) && <Note>{fmtVal(d.rationale)}</Note>}
    </>
  );
}

function OutcomeSections({ node }: { node: GraphNodeData }) {
  const d = node.data ?? {};
  const metrics = (d.metrics ?? {}) as Record<string, unknown>;
  const moneyKeys = new Set(["attributed_revenue", "verified_new_customer_revenue", "base_fee"]);
  return (
    <>
      <Section label="RESULT">
        <Row label="Assessment" value={titleCase(node.status)} />
        {Object.entries(metrics).map(([k, v]) => (
          <Row key={k} label={titleCase(k)} value={moneyKeys.has(k) ? fmtMoney(v) : fmtVal(v)} />
        ))}
      </Section>
      <Section label="SYSTEM">
        <Row label="Simulated" value={fmtVal(d.is_simulated)} mono />
      </Section>
      {Boolean(d.is_simulated) && <Note>Demo outcome. Simulated rather than observed from a real campaign cycle.</Note>}
    </>
  );
}

function PortfolioPatternSections({ node }: { node: GraphNodeData }) {
  const d = node.data ?? {};
  return (
    <>
      <Section label="EVIDENCE">
        <Row label="Comparable cases" value={fmtVal(d.evidence_count)} />
        <Row label="Positive outcomes" value={fmtVal(d.positive_outcomes)} />
        <Row label="Hybrid success rate" value={typeof d.hybrid_success_rate === "number" ? `${Math.round(d.hybrid_success_rate * 100)}%` : "—"} />
      </Section>
      <Section label="SCOPE">
        <Row label="Visibility" value="Privacy-safe AP portfolio" />
      </Section>
      {Boolean(d.synthetic) && <Note>Synthetic cross-client pattern — clearly labeled, not real client data.</Note>}
    </>
  );
}

/** Inline "Current renewal ask [$______]" control (spec Phase 5 Sec.4: "Do
 * not invent" a renewal ask - collect it before ever calling the endpoint,
 * rather than parsing free text or guessing). Collapsed to a single button
 * until clicked, then reveals the input. */
function CompareScenariosControl({ partnerId, onCompareScenarios, busy }: { partnerId: string; onCompareScenarios?: (partnerId: string, currentAsk: number) => void; busy?: boolean }) {
  const [open, setOpen] = useState(false);
  const [ask, setAsk] = useState("");
  if (!onCompareScenarios) return null;

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          marginTop: 26, fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8,
          border: `1px solid ${ACCENT.blue}`, background: "transparent", color: ACCENT.blue, cursor: "pointer",
        }}
      >
        Compare scenarios
      </button>
    );
  }

  const parsed = Number(ask.replace(/[^0-9.]/g, ""));
  const valid = ask.trim() !== "" && Number.isFinite(parsed) && parsed > 0;

  return (
    <div style={{ marginTop: 26 }}>
      <div style={{ fontSize: 12, color: TEXT.metadata, marginBottom: 6 }}>Current renewal ask</div>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={ask}
          onChange={(e) => setAsk(e.target.value)}
          placeholder="$6,000"
          autoFocus
          style={{ flex: 1, fontSize: 13, borderRadius: 8, border: `1px solid ${SURFACE_SEPARATOR}`, background: "transparent", color: TEXT.primary, padding: "8px 10px", outline: "none" }}
        />
        <button
          disabled={!valid || busy}
          onClick={() => valid && onCompareScenarios(partnerId, parsed)}
          style={{
            fontSize: 13, fontWeight: 600, padding: "8px 14px", borderRadius: 8, border: "none",
            background: ACCENT.blue, color: "#0a1622", cursor: valid ? "pointer" : "default", opacity: valid && !busy ? 1 : 0.5,
          }}
        >
          Compare
        </button>
      </div>
    </div>
  );
}

const SURFACE_SEPARATOR = "#151b26";

function PartnerSections({
  node, onGeneratePartnerBrief, busy, onWhatChanged, onCompareScenarios, scenarioComparisonBusy,
}: {
  node: GraphNodeData;
  onGeneratePartnerBrief?: (partnerId: string) => void;
  busy?: boolean;
  onWhatChanged?: (subjectType: string, subjectId: string) => void;
  onCompareScenarios?: (partnerId: string, currentAsk: number) => void;
  scenarioComparisonBusy?: boolean;
}) {
  const d = node.data ?? {};
  const isCreator = node.node_type === "creator";
  return (
    <>
      <Section label="OVERVIEW">
        {Boolean(d.platform) && <Row label="Platform" value={fmtVal(d.platform)} />}
        {isCreator && Boolean(d.follower_tier) && <Row label="Follower tier" value={fmtVal(d.follower_tier)} />}
        {!isCreator && Boolean(d.network) && <Row label="Network" value={fmtVal(d.network)} />}
        {!isCreator && Boolean(d.publisher_type) && <Row label="Publisher type" value={fmtVal(d.publisher_type)} />}
      </Section>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {onGeneratePartnerBrief && (
          <button
            disabled={busy}
            onClick={() => onGeneratePartnerBrief(rawId(node))}
            style={{
              marginTop: 26, fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8,
              border: "none", background: ACCENT.blue, color: "#0a1622", cursor: "pointer", opacity: busy ? 0.6 : 1,
            }}
          >
            Generate partner brief
          </button>
        )}
        <WhatChangedButton node={node} onWhatChanged={onWhatChanged} />
      </div>
      <CompareScenariosControl partnerId={rawId(node)} onCompareScenarios={onCompareScenarios} busy={scenarioComparisonBusy} />
    </>
  );
}

const PLANNED_ACTION_STATUSES = ["approved", "in_progress", "completed", "cancelled"] as const;
const ACTION_TYPE_LABEL: Record<string, string> = {
  renew: "Renew", renegotiate: "Renegotiate", test: "Test", expand: "Expand",
  pause: "Pause", review_measurement: "Review measurement", follow_up: "Follow up",
};

function PlanSections({ node, graph }: { node: GraphNodeData; graph: GraphResponse | null }) {
  const d = node.data ?? {};
  const clientEdge = (graph?.edges ?? []).find((e) => e.target === node.id && e.relationship === "HAS_PLAN");
  const client = clientEdge ? graph?.nodes.find((n) => n.id === clientEdge.source) : undefined;
  const actions = (graph?.nodes ?? []).filter(
    (n) => n.node_type === "planned_action" && graph?.edges.some((e) => e.source === node.id && e.target === n.id && e.relationship === "CONTAINS_ACTION"),
  );

  return (
    <>
      <Section label="PLAN">
        <Row label="Client" value={client?.label ?? "—"} />
        <Row label="Planning period" value={fmtVal(d.planning_period)} />
        <Row label="Objective" value={fmtVal(d.objective)} />
        <Row label="Actions" value={fmtVal(d.action_count)} />
        <Row label="Created" value={typeof d.created_at === "string" ? d.created_at.slice(0, 10) : "—"} mono />
      </Section>
      {actions.length > 0 && (
        <Section label="PLANNED ACTIONS">
          {actions.map((a) => (
            <Row
              key={a.id}
              label={`${ACTION_TYPE_LABEL[a.data.action_type as string] ?? titleCase(a.data.action_type as string)} · ${a.data.partner_name ?? "—"}`}
              value={titleCase(a.status ?? "")}
            />
          ))}
        </Section>
      )}
    </>
  );
}

function PlannedActionSections({
  node, graph, onUpdatePlannedAction, busy,
}: {
  node: GraphNodeData;
  graph: GraphResponse | null;
  onUpdatePlannedAction?: (actionId: string, patch: { status?: string; owner_id?: string | null; due_date?: string | null }) => void;
  busy?: boolean;
}) {
  const d = node.data ?? {};
  const [status, setStatus] = useState((node.status as string) ?? "approved");
  const [ownerId, setOwnerId] = useState((d.owner_id as string) ?? "");
  const [dueDate, setDueDate] = useState((d.due_date as string) ?? "");
  const teamMembers = (graph?.nodes ?? []).filter((n) => n.node_type === "team_member");

  const supportingMemoryIds = Array.isArray(d.supporting_memory_ids) ? (d.supporting_memory_ids as string[]) : [];
  const supportingCampaignIds = Array.isArray(d.supporting_campaign_ids) ? (d.supporting_campaign_ids as string[]) : [];

  const dirty = status !== ((node.status as string) ?? "approved") || ownerId !== ((d.owner_id as string) ?? "") || dueDate !== ((d.due_date as string) ?? "");

  return (
    <>
      <div style={{ marginTop: 12, fontSize: 11, letterSpacing: "0.09em", color: ACCENT.purple, fontFamily: "var(--font-mono-ui)" }}>PLANNED ACTION</div>
      <Section label="DETAILS">
        <Row label="Partner" value={fmtVal(d.partner_name)} />
        <Row label="Type" value={ACTION_TYPE_LABEL[d.action_type as string] ?? titleCase(d.action_type as string)} />
        {d.source_scenario_id != null && <Row label="Source scenario" value={fmtVal(d.source_scenario_id)} mono />}
        {d.source_decision_id != null && <Row label="Source decision" value={fmtVal(d.source_decision_id)} mono />}
        <Row label="Created" value={typeof d.created_at === "string" ? d.created_at.slice(0, 10) : "—"} mono />
      </Section>

      <Section label="RATIONALE">
        <Note>{fmtVal(d.rationale)}</Note>
      </Section>

      {(supportingMemoryIds.length > 0 || supportingCampaignIds.length > 0) && (
        <Section label="SUPPORTING EVIDENCE">
          {supportingMemoryIds.length > 0 && <Row label="Governed memory" value={`${supportingMemoryIds.length} referenced`} />}
          {supportingCampaignIds.length > 0 && <Row label="Campaigns" value={`${supportingCampaignIds.length} referenced`} />}
        </Section>
      )}

      <Section label="STATUS & OWNER">
        <div>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 4 }}>Status</div>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            style={{ width: "100%", fontSize: 13.5, borderRadius: 8, border: `1px solid ${SURFACE_SEPARATOR}`, background: "transparent", color: TEXT.primary, padding: "7px 8px" }}
          >
            {PLANNED_ACTION_STATUSES.map((s) => (
              <option key={s} value={s} style={{ background: "#0d1219" }}>{titleCase(s)}</option>
            ))}
          </select>
        </div>
        <div>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 4 }}>Owner</div>
          <select
            value={ownerId}
            onChange={(e) => setOwnerId(e.target.value)}
            style={{ width: "100%", fontSize: 13.5, borderRadius: 8, border: `1px solid ${SURFACE_SEPARATOR}`, background: "transparent", color: TEXT.primary, padding: "7px 8px" }}
          >
            <option value="" style={{ background: "#0d1219" }}>Unassigned</option>
            {teamMembers.map((m) => (
              <option key={m.id} value={m.id.split(":").slice(1).join(":")} style={{ background: "#0d1219" }}>{m.label}</option>
            ))}
          </select>
        </div>
        <div>
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 4 }}>Due date</div>
          <input
            type="text"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            placeholder="YYYY-MM-DD"
            style={{ width: "100%", fontSize: 13.5, borderRadius: 8, border: `1px solid ${SURFACE_SEPARATOR}`, background: "transparent", color: TEXT.primary, padding: "7px 8px" }}
          />
        </div>
        {onUpdatePlannedAction && (
          <button
            disabled={!dirty || busy}
            onClick={() => onUpdatePlannedAction(rawId(node), { status, owner_id: ownerId || null, due_date: dueDate || null })}
            style={{
              marginTop: 4, fontSize: 13, fontWeight: 600, padding: "8px 14px", borderRadius: 8, border: "none",
              background: ACCENT.blue, color: "#0a1622", cursor: "pointer", opacity: dirty && !busy ? 1 : 0.5,
            }}
          >
            Save
          </button>
        )}
      </Section>
    </>
  );
}

function TeamMemberSections({ node, graph }: { node: GraphNodeData; graph: GraphResponse | null }) {
  const d = node.data ?? {};
  const managed = (graph?.nodes ?? []).filter(
    (n) => n.node_type === "client" && graph?.edges.some((e) => e.source === node.id && e.target === n.id && e.relationship === "MANAGES"),
  );
  return (
    <Section label="OVERVIEW">
      {Boolean(d.role) && <Row label="Role" value={fmtVal(d.role)} />}
      {managed.map((c) => (
        <Row key={c.id} label="Client" value={c.label} />
      ))}
    </Section>
  );
}

export function MemoryInspector({
  node,
  graph = null,
  onReviewCampaign,
  campaignReviewBusy = false,
  onGeneratePartnerBrief,
  partnerBriefBusy = false,
  onViewHistory,
  onWhatChanged,
  onCompareScenarios,
  scenarioComparisonBusy = false,
  onBuildPlan,
  planBuildBusy = false,
  onUpdatePlannedAction,
  plannedActionUpdateBusy = false,
}: {
  node: GraphNodeData | null;
  graph?: GraphResponse | null;
  /** Wired to ChatPanel via LiveDemoView - see reviewCampaignRequest there. */
  onReviewCampaign?: (campaignId: string) => void;
  campaignReviewBusy?: boolean;
  /** Wired to ChatPanel via LiveDemoView - see partnerBriefRequest there. */
  onGeneratePartnerBrief?: (partnerId: string) => void;
  partnerBriefBusy?: boolean;
  /** Wired to ChatPanel via LiveDemoView - see memoryHistoryRequest there
   * ("View history" on a MemoryClaim node, Phase 4). */
  onViewHistory?: (subjectType: string, subjectId: string, predicate: string) => void;
  /** Wired to ChatPanel via LiveDemoView - see whatChangedRequest there
   * ("What changed?" on a Client/Partner node, Phase 4). */
  onWhatChanged?: (subjectType: string, subjectId: string) => void;
  /** Wired to ChatPanel via LiveDemoView - see scenarioComparisonRequest
   * there ("Compare scenarios" on a Partner node, Phase 5). */
  onCompareScenarios?: (partnerId: string, currentAsk: number) => void;
  scenarioComparisonBusy?: boolean;
  /** Wired to ChatPanel via LiveDemoView - see planBuildRequest there
   * ("Build plan" on the Client node, Phase 6). */
  onBuildPlan?: (planningPeriod: string | undefined) => void;
  planBuildBusy?: boolean;
  /** Direct PATCH, no chat round-trip needed - the action id is already known. */
  onUpdatePlannedAction?: (actionId: string, patch: { status?: string; owner_id?: string | null; due_date?: string | null }) => void;
  plannedActionUpdateBusy?: boolean;
}) {
  if (!node) {
    return (
      <div style={{ height: "100%", minHeight: 0, padding: 22 }}>
        <div style={{ fontSize: 13, color: TEXT.secondary2, fontStyle: "italic" }}>Click a node in the graph to inspect its memory metadata, source, and status.</div>
      </div>
    );
  }

  const desc = describeNode(node, graph);
  // Same family color the graph node itself uses for its type label/focus
  // ring, carried into the inspector so a node and its Context pane read as
  // the same object at a glance (spec follow-up: node-type color now maps
  // 1:1 into this pane, not just the graph canvas).
  const familyColor = FAMILIES[desc.family].text;

  return (
    <div className="ap-scroll" style={{ height: "100%", overflowY: "auto", padding: 22, minHeight: 0 }}>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 16 }}>CONTEXT</div>
      <div style={{ fontSize: 19, fontWeight: 600, color: TEXT.primary, lineHeight: 1.3, whiteSpace: "pre-line" }}>{node.label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 7, marginTop: 3 }}>
        <span style={{ width: 6, height: 6, borderRadius: 2, background: familyColor, flex: "none" }} />
        <span style={{ fontSize: 13, color: familyColor }}>{desc.typeLabel}</span>
      </div>
      {desc.statusText && <div style={{ fontSize: 13, color: familyColor, marginTop: 12 }}>{desc.statusText}</div>}

      {node.node_type === "client" && <ClientSections node={node} graph={graph} onWhatChanged={onWhatChanged} onBuildPlan={onBuildPlan} planBuildBusy={planBuildBusy} />}
      {node.node_type === "memory_claim" && <MemoryClaimSections node={node} graph={graph} onViewHistory={onViewHistory} />}
      {node.node_type === "campaign" && <CampaignSections node={node} onReviewCampaign={onReviewCampaign} busy={campaignReviewBusy} />}
      {node.node_type === "decision" && <DecisionSections node={node} graph={graph} />}
      {node.node_type === "outcome" && <OutcomeSections node={node} />}
      {node.node_type === "portfolio_pattern" && <PortfolioPatternSections node={node} />}
      {node.node_type === "plan" && <PlanSections node={node} graph={graph} />}
      {node.node_type === "planned_action" && (
        <PlannedActionSections node={node} graph={graph} onUpdatePlannedAction={onUpdatePlannedAction} busy={plannedActionUpdateBusy} />
      )}
      {(node.node_type === "creator" || node.node_type === "publisher") && (
        <PartnerSections
          node={node}
          onGeneratePartnerBrief={onGeneratePartnerBrief}
          busy={partnerBriefBusy}
          onWhatChanged={onWhatChanged}
          onCompareScenarios={onCompareScenarios}
          scenarioComparisonBusy={scenarioComparisonBusy}
        />
      )}
      {node.node_type === "team_member" && <TeamMemberSections node={node} graph={graph} />}
    </div>
  );
}
