import type { GraphEdgeData, GraphResponse } from "./types";

export function withoutRelationshipClaims(graph: GraphResponse): GraphResponse {
  const dropIds = new Set(
    graph.nodes.filter((n) => n.node_type === "memory_claim" && n.data?.predicate === "relationship_status").map((n) => n.id),
  );
  if (dropIds.size === 0) return graph;
  return {
    nodes: graph.nodes.filter((n) => !dropIds.has(n.id)),
    edges: graph.edges.filter((e) => !dropIds.has(e.source) && !dropIds.has(e.target)),
  };
}

export function withDerivedEdges(graph: GraphResponse): GraphResponse {
  const existing = new Set(graph.edges.map((e) => `${e.source}|${e.target}|${e.relationship}`));
  const derived: GraphEdgeData[] = [];

  function addDerived(source: string, target: string, relationship: string) {
    const key = `${source}|${target}|${relationship}`;
    if (existing.has(key)) return;
    existing.add(key);
    derived.push({ id: `derived:${source}->${target}:${relationship}`, source, target, relationship });
  }

  const campaignToPartner = new Map<string, string>();
  graph.edges.forEach((e) => {
    if (e.relationship === "APPLIES_TO") campaignToPartner.set(e.source, e.target);
  });
  graph.edges.forEach((e) => {
    if (e.relationship !== "HAS_CAMPAIGN") return;
    const partnerId = campaignToPartner.get(e.target);
    if (partnerId) addDerived(e.source, partnerId, "HAS_RELATIONSHIP");
  });

  const partnerIds = new Set(graph.nodes.filter((n) => n.node_type === "creator" || n.node_type === "publisher").map((n) => n.id));
  graph.nodes.forEach((n) => {
    if (n.node_type !== "memory_claim") return;
    const subjectType = n.data?.subject_type;
    const subjectId = n.data?.subject_id;
    if (subjectType !== "creator" && subjectType !== "publisher") return;
    const partnerNodeId = `partner:${subjectId}`;
    if (!partnerIds.has(partnerNodeId)) return;
    addDerived(partnerNodeId, n.id, "HAS_MEMORY");
  });

  return derived.length > 0 ? { ...graph, edges: [...graph.edges, ...derived] } : graph;
}
