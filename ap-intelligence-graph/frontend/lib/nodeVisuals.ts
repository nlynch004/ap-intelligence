// Business-readable presentation for graph nodes/edges (design_handoff v2).
// Distinguishes node kinds and memory status using semantic color family +
// business-meaning type label + status glyph - never color alone. Everything
// here is derived from real API fields (GraphNodeData.data /
// GraphResponse.edges); nothing is hardcoded to the Northwind demo script.

import type { Family } from "./design";
import { humanize, predicateLabel, sentenceCase, titleCase } from "./design";
import type { GraphEdgeData, GraphNodeData, GraphResponse } from "./types";

export interface NodeDescription {
  family: Family;
  /** Business-meaning label shown above the title, e.g. "Strategy", "Decision". */
  typeLabel: string;
  /** May contain "\n" for a two-line title (campaign nodes). */
  title: string;
  detail: string | null;
  /** Includes its glyph, e.g. "✓ Accepted", "△ Review required". */
  statusText: string | null;
  synthetic: boolean;
  /** Historical/superseded treatment: dimmed resting opacity, muted text. */
  historical: boolean;
}

const HISTORICAL_STATUSES = new Set(["superseded", "expired", "deprecated"]);

function asString(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}
function asNumber(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}

function describeClient(node: GraphNodeData, graph?: GraphResponse | null): NodeDescription {
  const d = node.data ?? {};
  const industry = asString(d.industry);
  const campaignCount = graph
    ? graph.edges.filter((e) => e.source === node.id && e.relationship === "HAS_CAMPAIGN").length
    : undefined;
  const parts = [
    industry,
    campaignCount != null ? `${campaignCount} open campaign${campaignCount === 1 ? "" : "s"}` : null,
  ].filter(Boolean);
  return {
    family: "blue",
    typeLabel: "Client",
    title: node.label,
    detail: parts.length ? parts.join(" · ") : null,
    statusText: "● Active relationship",
    synthetic: Boolean(d.synthetic),
    historical: false,
  };
}

function describeTeamMember(node: GraphNodeData, graph?: GraphResponse | null): NodeDescription {
  const d = node.data ?? {};
  const role = asString(d.role);
  const managedClient = graph
    ? graph.nodes.find((n) =>
        graph.edges.some((e) => e.source === node.id && e.target === n.id && e.relationship === "MANAGES") &&
        n.node_type === "client",
      )
    : undefined;
  return {
    family: "gray",
    typeLabel: role || "Team member",
    title: node.label,
    detail: managedClient ? `Manages ${managedClient.label}` : null,
    statusText: null,
    synthetic: Boolean(d.synthetic),
    historical: false,
  };
}

function describePartner(node: GraphNodeData): NodeDescription {
  const d = node.data ?? {};
  const platform = asString(d.platform);
  const isCreator = node.node_type === "creator";
  const parts = isCreator
    ? [platform, asString(d.follower_tier) ? `${titleCase(d.follower_tier as string)} tier` : null]
    : [asString(d.network), asString(d.publisher_type)];
  const detail = parts.filter(Boolean).join(" · ") || platform || null;
  return {
    family: isCreator ? "teal" : "rose",
    typeLabel: isCreator ? "Creator" : "Publisher",
    title: node.label,
    detail: detail || null,
    statusText: null,
    synthetic: Boolean(d.synthetic),
    historical: false,
  };
}

function describeCampaign(node: GraphNodeData): NodeDescription {
  const d = node.data ?? {};
  const fee = asNumber(d.flat_fee);
  const revenue = asNumber(d.attributed_revenue);
  const roas = fee && revenue != null ? revenue / fee : null;
  const parts = [fee != null ? `$${fee.toLocaleString()} fee` : null, roas != null ? `${roas.toFixed(2)}x ROAS` : null];
  return {
    family: "sage",
    typeLabel: "Campaign",
    title: node.label,
    detail: parts.filter(Boolean).join(" · ") || null,
    statusText: null,
    synthetic: false,
    historical: false,
  };
}

function describeMemoryClaim(node: GraphNodeData): NodeDescription {
  const d = node.data ?? {};
  const status = node.status ?? undefined;
  const claimClass = asString(d.claim_class);
  const predicate = asString(d.predicate) ?? "";
  const value = asString(d.value) ?? node.label;
  const historical = Boolean(status && HISTORICAL_STATUSES.has(status));
  const isHypothesis = claimClass === "hypothesis" || status === "needs_review";

  let family: Family = "blue";
  let statusText = "● Active";
  if (historical) {
    family = "hist";
    statusText = "Historical";
  } else if (isHypothesis) {
    family = "amber";
    statusText = "△ Review required";
  }

  return {
    family,
    typeLabel: predicateLabel(predicate),
    title: sentenceCase(value),
    detail: null,
    statusText,
    synthetic: Boolean(d.synthetic),
    historical,
  };
}

const DECISION_STATUS_TEXT: Record<string, string> = {
  approved: "✓ Accepted",
  rejected: "✕ Rejected",
};

function describeDecision(node: GraphNodeData): NodeDescription {
  const d = node.data ?? {};
  const terms = d.terms as { base_fee?: number; performance_bonus_pct?: number } | undefined;
  const detail =
    terms && terms.base_fee != null
      ? `$${terms.base_fee.toLocaleString()} base${terms.performance_bonus_pct ? ` + ${terms.performance_bonus_pct}% bonus` : ""}`
      : null;
  const status = node.status ?? "";
  return {
    family: "green",
    typeLabel: "Decision",
    title: node.label,
    detail,
    statusText: DECISION_STATUS_TEXT[status] ?? (status ? `● ${sentenceCase(status)}` : null),
    synthetic: Boolean(d.synthetic),
    historical: false,
  };
}

function describeOutcome(node: GraphNodeData): NodeDescription {
  const d = node.data ?? {};
  const metrics = (d.metrics ?? {}) as Record<string, unknown>;
  const revenue = asNumber(metrics.attributed_revenue);
  const title = revenue != null ? `+$${Math.round(revenue).toLocaleString()} attributed revenue` : node.label;
  return {
    family: "green",
    typeLabel: "Outcome",
    title,
    detail: null,
    statusText: d.is_simulated ? "✓ Simulated result" : "● Recorded",
    synthetic: false,
    historical: false,
  };
}

function describePortfolioPattern(node: GraphNodeData): NodeDescription {
  const d = node.data ?? {};
  const count = asNumber(d.evidence_count);
  return {
    family: "purple",
    typeLabel: "Portfolio pattern",
    title: node.label,
    detail: count != null ? `${count} comparable case${count === 1 ? "" : "s"}` : null,
    statusText: null,
    synthetic: Boolean(d.synthetic),
    historical: false,
  };
}

export function describeNode(node: GraphNodeData, graph?: GraphResponse | null): NodeDescription {
  switch (node.node_type) {
    case "client":
      return describeClient(node, graph);
    case "team_member":
      return describeTeamMember(node, graph);
    case "creator":
    case "publisher":
      return describePartner(node);
    case "campaign":
      return describeCampaign(node);
    case "memory_claim":
      return describeMemoryClaim(node);
    case "decision":
      return describeDecision(node);
    case "outcome":
      return describeOutcome(node);
    case "portfolio_pattern":
      return describePortfolioPattern(node);
    default:
      return {
        family: "gray",
        typeLabel: titleCase(node.node_type),
        title: node.label,
        detail: null,
        statusText: null,
        synthetic: false,
        historical: false,
      };
  }
}

// ---- edges ----

export interface EdgeDescription {
  family: Family;
  label: string;
  dashed: boolean;
  alwaysLabeled: boolean;
  animated: boolean;
}

interface EdgeSpec {
  label: string;
  family?: Family;
  dashed?: boolean;
  always?: boolean;
  animated?: boolean;
  /** Color communicates *what kind of evidence* motivated this edge, so its
   * family follows the target node rather than a fixed color. */
  familyFromTarget?: boolean;
}

const EDGE_TABLE: Record<string, EdgeSpec> = {
  MANAGES: { label: "manages", family: "gray" },
  WORKED_WITH: { label: "worked with", family: "gray" },
  // Color follows the target - a relationship_status memory claim (blue) or
  // a creator/publisher (teal/rose) - so the edge visually previews what
  // it's about, same as MOTIVATED_BY below.
  HAS_RELATIONSHIP: { label: "has relationship", familyFromTarget: true },
  HAS_CAMPAIGN: { label: "has campaign", family: "gray" },
  APPLIES_TO: { label: "applies to", family: "gray" },
  HAS_STRATEGY: { label: "current strategy", family: "blue" },
  HAS_GOAL: { label: "has goal", family: "blue" },
  HAS_MEMORY: { label: "has memory", family: "blue" },
  HAS_RISK: { label: "raises risk", family: "amber", dashed: true },
  SUPERSEDES: { label: "supersedes", family: "hist", dashed: true, always: true },
  MOTIVATED_BY: { label: "motivated by", dashed: true, familyFromTarget: true },
  MADE_DECISION: { label: "made decision", family: "green" },
  RESULTED_IN: { label: "resulted in", family: "green", always: true, animated: true },
  SUPPORTS: { label: "supports", family: "purple" },
};

export function edgeStyle(edge: GraphEdgeData, targetFamily: Family): EdgeDescription {
  const spec = EDGE_TABLE[edge.relationship];
  if (!spec) {
    return { family: "gray", label: humanize(edge.relationship).toLowerCase(), dashed: false, alwaysLabeled: false, animated: false };
  }
  return {
    family: spec.familyFromTarget ? targetFamily : spec.family ?? "gray",
    label: spec.label,
    dashed: Boolean(spec.dashed),
    alwaysLabeled: Boolean(spec.always),
    animated: Boolean(spec.animated),
  };
}
