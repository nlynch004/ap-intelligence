// Visual semantics for graph nodes (spec Sec.27): distinguish node kinds and
// memory status using more than color alone - icon, border style, and
// opacity for historical/superseded nodes.

import type { GraphNodeData } from "./types";

export interface NodeVisual {
  icon: string;
  accent: string; // tailwind border/text color class fragment
  bg: string;
  border: string;
  dashed: boolean;
  faded: boolean;
  badge?: string;
}

export function visualFor(node: GraphNodeData): NodeVisual {
  const claimClass = node.data?.claim_class as string | undefined;
  const status = node.status;

  switch (node.node_type) {
    case "client":
      return { icon: "\u{1F3E2}", accent: "text-slate-700", bg: "bg-white", border: "border-slate-400", dashed: false, faded: false };
    case "creator":
      return { icon: "\u{1F3A8}", accent: "text-indigo-700", bg: "bg-indigo-50", border: "border-indigo-300", dashed: false, faded: false };
    case "publisher":
      return { icon: "\u{1F4F0}", accent: "text-teal-700", bg: "bg-teal-50", border: "border-teal-300", dashed: false, faded: false };
    case "campaign":
      return { icon: "\u{1F4E3}", accent: "text-amber-700", bg: "bg-amber-50", border: "border-amber-300", dashed: false, faded: false };
    case "team_member":
      return { icon: "\u{1F464}", accent: "text-slate-600", bg: "bg-slate-50", border: "border-slate-300", dashed: false, faded: false };
    case "decision":
      return { icon: "✅", accent: "text-emerald-800", bg: "bg-emerald-50", border: "border-emerald-400", dashed: false, faded: false, badge: status ?? undefined };
    case "outcome":
      return { icon: status === "positive" ? "\u{1F4C8}" : "\u{1F4C9}", accent: "text-emerald-800", bg: "bg-emerald-50", border: "border-emerald-400", dashed: false, faded: false, badge: node.data?.is_simulated ? "simulated" : undefined };
    case "portfolio_pattern":
      return { icon: "\u{1F4CA}", accent: "text-purple-800", bg: "bg-purple-50", border: "border-purple-300", dashed: false, faded: false, badge: `${node.data?.evidence_count ?? "?"} cases` };
    case "memory_claim":
      if (status === "superseded" || status === "expired" || status === "deprecated") {
        return { icon: "\u{1F5C4}️", accent: "text-slate-400", bg: "bg-slate-50", border: "border-slate-300", dashed: true, faded: true, badge: status };
      }
      if (claimClass === "hypothesis" || status === "needs_review") {
        return { icon: "⚠️", accent: "text-amber-800", bg: "bg-amber-50", border: "border-amber-400", dashed: true, faded: false, badge: "hypothesis" };
      }
      return { icon: "\u{1F9E0}", accent: "text-blue-800", bg: "bg-blue-50", border: "border-blue-300", dashed: false, faded: false, badge: "active" };
    default:
      return { icon: "●", accent: "text-slate-600", bg: "bg-white", border: "border-slate-300", dashed: false, faded: false };
  }
}
