"use client";

import { FAMILIES, FONT_MONO, TEXT, predicateLabel, sentenceCase, titleCase } from "@/lib/design";
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

function ClientSections({ node, graph }: { node: GraphNodeData; graph: GraphResponse | null }) {
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
    </>
  );
}

function MemoryClaimSections({ node, graph }: { node: GraphNodeData; graph: GraphResponse | null }) {
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
    </>
  );
}

function CampaignSections({ node }: { node: GraphNodeData }) {
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

function PartnerSections({ node }: { node: GraphNodeData }) {
  const d = node.data ?? {};
  const isCreator = node.node_type === "creator";
  return (
    <Section label="OVERVIEW">
      {Boolean(d.platform) && <Row label="Platform" value={fmtVal(d.platform)} />}
      {isCreator && Boolean(d.follower_tier) && <Row label="Follower tier" value={fmtVal(d.follower_tier)} />}
      {!isCreator && Boolean(d.network) && <Row label="Network" value={fmtVal(d.network)} />}
      {!isCreator && Boolean(d.publisher_type) && <Row label="Publisher type" value={fmtVal(d.publisher_type)} />}
    </Section>
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

export function MemoryInspector({ node, graph = null }: { node: GraphNodeData | null; graph?: GraphResponse | null }) {
  if (!node) {
    return (
      <div style={{ flex: 1.15, minHeight: 0, padding: 22 }}>
        <div style={{ fontSize: 13, color: TEXT.secondary2, fontStyle: "italic" }}>Click a node in the graph to inspect its memory metadata, source, and status.</div>
      </div>
    );
  }

  const desc = describeNode(node, graph);
  const statusColor = FAMILIES[desc.family].text;

  return (
    <div className="ap-scroll" style={{ flex: 1.15, overflowY: "auto", padding: 22, minHeight: 0 }}>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 16 }}>CONTEXT</div>
      <div style={{ fontSize: 19, fontWeight: 600, color: TEXT.primary, lineHeight: 1.3, whiteSpace: "pre-line" }}>{node.label}</div>
      <div style={{ fontSize: 13, color: TEXT.metadata, marginTop: 3 }}>{desc.typeLabel}</div>
      {desc.statusText && <div style={{ fontSize: 13, color: statusColor, marginTop: 12 }}>{desc.statusText}</div>}

      {node.node_type === "client" && <ClientSections node={node} graph={graph} />}
      {node.node_type === "memory_claim" && <MemoryClaimSections node={node} graph={graph} />}
      {node.node_type === "campaign" && <CampaignSections node={node} />}
      {node.node_type === "decision" && <DecisionSections node={node} graph={graph} />}
      {node.node_type === "outcome" && <OutcomeSections node={node} />}
      {node.node_type === "portfolio_pattern" && <PortfolioPatternSections node={node} />}
      {(node.node_type === "creator" || node.node_type === "publisher") && <PartnerSections node={node} />}
      {node.node_type === "team_member" && <TeamMemberSections node={node} graph={graph} />}
    </div>
  );
}
