export type Family = "blue" | "green" | "amber" | "purple" | "gray" | "hist" | "teal" | "rose" | "sage";

export interface FamilyTokens {
  line: string;
  node: string;
  border: string;
  text: string;
  glow: string;
}

export const FAMILIES: Record<Family, FamilyTokens> = {
  blue: { line: "#4a7fa8", node: "#0e1620", border: "#1c2b3a", text: "#8fbfe3", glow: "rgba(91,159,212,0.22)" },
  green: { line: "#3f8f6d", node: "#0d1a17", border: "#1b3229", text: "#6fd0a5", glow: "rgba(79,185,141,0.22)" },
  amber: { line: "#9c7745", node: "#191510", border: "#33291b", text: "#d2a468", glow: "rgba(201,151,90,0.2)" },
  purple: { line: "#6d61a4", node: "#14131f", border: "#272338", text: "#a599dd", glow: "rgba(143,131,201,0.2)" },
  gray: { line: "#333d4e", node: "#0c1017", border: "#181e29", text: "#8896ac", glow: "rgba(120,140,170,0.12)" },
  hist: { line: "#3a4557", node: "#0a0e14", border: "#151b25", text: "#5d6b81", glow: "rgba(120,140,170,0.08)" },
  teal: { line: "#3f8f8a", node: "#0d1917", border: "#1b2f2b", text: "#7ecec6", glow: "rgba(79,185,175,0.2)" },
  rose: { line: "#a35a78", node: "#1a1015", border: "#301f28", text: "#d99bb5", glow: "rgba(190,110,150,0.2)" },
  sage: { line: "#7d8659", node: "#14160f", border: "#262a1c", text: "#b6c194", glow: "rgba(175,190,130,0.18)" },
};

export const ACCENT = {
  blue: "#5b9fd4",
  green: "#4fb98d",
  amber: "#c9975a",
  purple: "#8f83c9",
  historical: "#3d4859",
  teal: "#5fc2ba",
  rose: "#c97fa0",
  sage: "#a3b177",
};

export const SURFACE = {
  app: "#090c12",
  panel: "#0b0f16",
  raised: "#0d1219",
  activeRow: "#111823",
  nodeResting: "#0c1017",
  nodeHistorical: "#0a0e14",
  separator: "#151b26",
  separatorInner: "#141a25",
  separatorInner2: "#161d28",
  timelineRail: "#1a2130",
  nodeBorderResting: "#151b25",
};

export const TEXT = {
  primary: "#e6ecf5",
  strongSecondary: "#dbe4f0",
  strongSecondary2: "#c3cfe0",
  secondary: "#94a3ba",
  secondary2: "#8c98ad",
  metadata: "#7b8aa3",
  faint: "#5c6a82",
  faint2: "#4f5d75",
  historicalTitle: "#7d889b",
  historicalStatus: "#5d6b81",
};

export const FONT_MONO = "var(--font-mono-ui)";

export function humanize(v: string | null | undefined): string {
  if (!v) return "";
  return v.replace(/_/g, " ");
}

export function sentenceCase(v: string | null | undefined): string {
  const h = humanize(v);
  return h ? h.charAt(0).toUpperCase() + h.slice(1) : "";
}

export function titleCase(v: string | null | undefined): string {
  return humanize(v)
    .split(" ")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export const PREDICATE_LABEL: Record<string, string> = {
  partnership_strategy: "Strategy",
  primary_growth_objective: "Primary objective",
  accepts_tradeoff: "Accepted tradeoff",
  relationship_status: "Relationship",
  negotiation_history: "Negotiation history",
  attribution_integrity_risk: "Attribution hypothesis",
  partner_performance_pattern: "Performance pattern",
};

export function predicateLabel(predicate: string): string {
  return PREDICATE_LABEL[predicate] ?? titleCase(predicate);
}
