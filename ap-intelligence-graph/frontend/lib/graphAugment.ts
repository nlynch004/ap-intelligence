// Presentation-layer graph augmentation: adds edges the backend's graph
// query doesn't materialize but that are already implied by data it does
// return, so focus-tracing/hover, the inspector's "RELATED" section, and
// the canvas itself all show relationships a user would reasonably expect
// to see a line for. Also drops one category of node that's redundant once
// that edge exists. See withoutRelationshipClaims / withDerivedEdges below.
//
// Deriving/filtering here (rather than in the backend) keeps this a pure
// presentation fix: nothing about memory governance, retrieval, or the API
// contract changes - the graph the UI renders just includes additional,
// clearly-derived relationships already implied by data already returned,
// and omits a node whose information is now fully carried by an edge. It
// does NOT fix cases where the LLM extraction itself mis-attributes a
// claim's subject_type to "client" when it should have been the named
// partner - that's an extraction-accuracy issue in agents/prompts.py, not
// something derivable from the graph after the fact.

import type { GraphEdgeData, GraphResponse } from "./types";

/**
 * Drops memory_claim nodes whose predicate is relationship_status. Once
 * withDerivedEdges (below) adds a direct client<->partner "has relationship"
 * edge, a dedicated node just to say "this is a relationship" duplicates
 * that same fact in a second form - the edge already carries it. Also drops
 * any edge touching a dropped node so nothing points at a node that no
 * longer exists. Applies generally (not just to the seeded example), so a
 * relationship_status claim created later via chat is filtered the same way.
 */
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

  // client -> creator/publisher, inferred transitively through
  // client -HAS_CAMPAIGN-> campaign -APPLIES_TO-> partner (there is no
  // direct edge for this even though a partner running a client's campaign
  // is, in plain terms, a relationship with that client). This is now the
  // *only* place "has relationship" is represented, since the claim-node
  // form of it is filtered out by withoutRelationshipClaims above.
  const campaignToPartner = new Map<string, string>();
  graph.edges.forEach((e) => {
    if (e.relationship === "APPLIES_TO") campaignToPartner.set(e.source, e.target);
  });
  graph.edges.forEach((e) => {
    if (e.relationship !== "HAS_CAMPAIGN") return;
    const partnerId = campaignToPartner.get(e.target);
    if (partnerId) addDerived(e.source, partnerId, "HAS_RELATIONSHIP");
  });

  // partner -> memory_claim, whenever the claim's own subject_type/subject_id
  // names a creator/publisher already present in this graph (e.g.
  // negotiation_history). relationship_status claims never reach here -
  // they're filtered out before this runs - so there's no predicate-specific
  // label to pick; every remaining partner-scoped claim uses the same
  // generic label the backend uses for client-claim edges.
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
