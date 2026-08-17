// Authored presenter content for the post-demo "Discussion Guide" tab.
// Static, hand-written talking points - no backend/API/LLM dependency and
// nothing derived from live graph or demo state. See components/DiscussionGuide.tsx
// for the renderer. Content is intentionally verbatim to the discussion brief
// this was drafted from, condensed only where that brief said to keep things
// compact (Section 02's RAG-vs-governed-memory comparison).

export interface TwoColumn {
  heading: string;
  bullets: string[];
}

export interface ResponsibilitiesSection {
  kind: "responsibilities";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  framing: string;
  llm: TwoColumn;
  app: TwoColumn;
  keyLines: string[];
}

export interface RagCompareSection {
  kind: "rag-compare";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  bullets: string[];
  keyLine: string;
  compare: { rag: TwoColumn; governed: TwoColumn };
}

export interface RealVsSimplifiedSection {
  kind: "real-vs-simplified";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  real: TwoColumn & { note: string };
  simplified: TwoColumn;
  keyLine: string;
}

export interface ArchitectureChain {
  heading?: string;
  steps: string[];
}

export interface ArchitectureSection {
  kind: "architecture";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  mainChain: ArchitectureChain;
  parallelChains: ArchitectureChain[];
  bullets: string[];
  keyLine: string;
  disclaimer: string;
}

export interface BulletsSimpleSection {
  kind: "bullets-simple";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  bullets: (string | { text: string; sub: string[] })[];
  keyLine: string;
}

export interface RankedRisk {
  rank: number;
  title: string;
  bullets: string[];
  mitigation: string;
}

export interface RankedRisksSection {
  kind: "ranked-risks";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  risks: RankedRisk[];
  keyLine: string;
}

export interface Phase {
  name: string;
  badge?: string;
  bullets: string[];
}

export interface PhasesSection {
  kind: "phases";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  opening: string;
  phases: Phase[];
  keyLine: string;
}

export interface AdoptionSection {
  kind: "adoption";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  opening: string;
  behaviors: string[];
  bullets: string[];
  stallSignals: string[];
  keyLine: string;
}

export interface MeasurementSection {
  kind: "measurement";
  id: string;
  num: string;
  navLabel: string;
  title: string;
  opening: string;
  groups: TwoColumn[];
  diagnostic: TwoColumn;
  keyLine: string;
}

export type DiscussionSection =
  | ResponsibilitiesSection
  | RagCompareSection
  | RealVsSimplifiedSection
  | ArchitectureSection
  | BulletsSimpleSection
  | RankedRisksSection
  | PhasesSection
  | AdoptionSection
  | MeasurementSection;

export const DISCUSSION_GUIDE_HEADER = {
  eyebrow: "POST-DEMO DISCUSSION",
  title: "Discussion Guide",
  tagline: "Architecture, production, rollout & measurement",
  subtitle: "How the prototype works, what changes in production, and how I would drive adoption and business value.",
};

export const DISCUSSION_SECTIONS: DiscussionSection[] = [
  {
    kind: "responsibilities",
    id: "llm-vs-app",
    num: "01",
    navLabel: "LLM vs App",
    title: "LLM vs. Application Responsibilities",
    framing: "Use the model for interpretation and reasoning; use deterministic software for control.",
    llm: {
      heading: "LLM responsibilities",
      bullets: [
        "Extract candidate memories from natural account-team conversation.",
        "Summarize relevant account context.",
        "Synthesize retrieved evidence into a recommendation.",
        "Explain rationale, uncertainty, and recommended terms.",
      ],
    },
    app: {
      heading: "Application responsibilities",
      bullets: [
        "Validate model output with Pydantic.",
        "Normalize predicates into governed vocabulary.",
        "Detect memory conflicts.",
        "Control CREATE, SUPERSEDE, review, and persistence.",
        "Enforce status, validity windows, scope, and source authority.",
        "Retrieve the actual evidence set.",
        "Calculate ROAS, fee changes, counts, and other hard metrics.",
        "Attach real supporting memory IDs.",
        "Persist decisions and outcomes.",
      ],
    },
    keyLines: [
      "The model proposes and reasons; application logic governs and persists.",
      "The LLM reasons over evidence. It does not own the evidence.",
    ],
  },
  {
    kind: "rag-compare",
    id: "why-not-rag",
    num: "02",
    navLabel: "Why not RAG",
    title: "Why Not Just RAG?",
    bullets: [
      "RAG helps retrieve relevant information.",
      "This workflow also requires knowledge lifecycle and governance.",
      "Client strategies become stale.",
      "New information can contradict an old belief.",
      "A hypothesis must not be treated like a verified fact.",
      "Historical knowledge sometimes needs to remain available without remaining active.",
      "Sources carry different levels of authority.",
      "Cross-client knowledge requires strict scope and privacy controls.",
    ],
    keyLine: "Embeddings can improve retrieval, but retrieval alone does not solve organizational memory governance.",
    compare: {
      rag: { heading: "RAG", bullets: ["Find relevant information.", "Put it into model context."] },
      governed: {
        heading: "Governed memory",
        bullets: [
          "Determine what is currently believed.",
          "Track why it is believed.",
          "Preserve source and authority.",
          "Manage contradictions and supersession.",
          "Preserve history.",
          "Control scope and privacy.",
        ],
      },
    },
  },
  {
    kind: "real-vs-simplified",
    id: "real-vs-simplified",
    num: "03",
    navLabel: "Real vs Simplified",
    title: "What Is Real vs. Simplified",
    real: {
      heading: "Real in the prototype",
      bullets: [
        "Live OpenAI calls.",
        "Natural-language memory extraction.",
        "Pydantic validation.",
        "Deterministic predicate normalization.",
        "Candidate-memory review.",
        "Conflict detection.",
        "SUPERSEDE lifecycle.",
        "Source, confidence, scope, authority, and validity metadata.",
        "SQLite persistence.",
        "Active-memory retrieval.",
        "Deterministic Decision Evidence.",
        "LLM recommendation reasoning.",
        "Server-derived supporting-memory IDs.",
        "Decision persistence.",
        "Outcome persistence.",
        "Portfolio evidence update 31 → 32.",
        "Live graph refresh.",
      ],
      note: "These behaviors were verified end-to-end during the final smoke test.",
    },
    simplified: {
      heading: "Simplified / synthetic",
      bullets: [
        "AP portfolio history is synthetic.",
        "Future commercial outcome is simulated.",
        "SQLite is prototype-scale.",
        "No enterprise SSO or RBAC.",
        "Cross-client privacy is represented by application scope/filtering rather than hard DB tenant isolation.",
        "No vector/semantic retrieval.",
        "No dedicated graph database.",
        "No actual AWS/AgentCore deployment.",
        "No production outcome-ingestion pipeline.",
      ],
    },
    keyLine: "The prototype behavior is real; the production infrastructure and portfolio history are deliberately simplified.",
  },
  {
    kind: "architecture",
    id: "production",
    num: "04",
    navLabel: "Production",
    title: "Prototype → Production",
    mainChain: {
      steps: ["APVision / Internal Product", "Application API", "Memory + Decision Services", "AgentCore Runtime", "Amazon Bedrock"],
    },
    parallelChains: [
      { heading: "Canonical memory", steps: ["Aurora PostgreSQL", "pgvector / semantic retrieval"] },
      { heading: "Raw evidence", steps: ["S3", "immutable raw evidence"] },
      { heading: "Governance & ops", steps: ["CloudWatch / IAM / KMS", "governance & operations"] },
    ],
    bullets: [
      "Move local FastAPI workloads into managed application/agent execution.",
      "Use Bedrock for governed foundation-model access.",
      "Move canonical memory from SQLite to Aurora PostgreSQL.",
      "Add pgvector or OpenSearch when semantic retrieval becomes necessary.",
      "Keep immutable source/evidence artifacts in S3.",
      "Add IAM, encryption, auditability, and observability.",
      "Use async workflows only where consolidation/review requires them.",
    ],
    keyLine: "I would preserve the application boundaries, not the local infrastructure.",
    disclaimer: "Target-state direction, not a claim that any of this is already implemented.",
  },
  {
    kind: "bullets-simple",
    id: "postgres-vs-graph",
    num: "05",
    navLabel: "Postgres vs Graph DB",
    title: "Why PostgreSQL Before Neptune?",
    bullets: [
      "A graph UI does not automatically require a graph database.",
      { text: "The canonical workload is still highly relational:", sub: ["claims", "statuses", "scopes", "validity windows", "sources", "decisions", "outcomes"] },
      "PostgreSQL provides mature transactions and governance.",
      "Graph relationships can remain explicit relational edge records initially.",
      "pgvector can add semantic retrieval without introducing a second canonical store.",
      "Neptune becomes valuable if complex multi-hop graph traversal becomes a dominant production workload.",
    ],
    keyLine: "The graph is a product representation; it does not have to dictate the storage engine.",
  },
  {
    kind: "ranked-risks",
    id: "scale",
    num: "06",
    navLabel: "200+ Clients",
    title: "What Breaks First at 200+ Clients?",
    risks: [
      {
        rank: 1,
        title: "Cross-client privacy",
        bullets: [
          "Application-level filters are not sufficient defense-in-depth.",
          "One missed tenant filter could expose proprietary information.",
          "Production needs hard tenant enforcement, authorization, and auditing.",
        ],
        mitigation: "PostgreSQL RLS or equivalent tenant isolation, RBAC, audit logs, privacy-safe aggregation.",
      },
      {
        rank: 2,
        title: "Memory quality and pollution",
        bullets: ["Thousands of low-value claims degrade retrieval.", "Stale or contradictory knowledge compounds over time."],
        mitigation: "Stricter write rules, expiration, review, consolidation, promotion/demotion, source authority.",
      },
      {
        rank: 3,
        title: "Retrieval volume",
        bullets: ["Current deterministic/Python retrieval will not scale indefinitely."],
        mitigation: "Indexes, SQL-side filtering, vector retrieval, reranking, context budgets.",
      },
      {
        rank: 4,
        title: "Ontology and entity resolution",
        bullets: ["Different clients and systems use different names and terminology.", "Hand-maintained aliases eventually become insufficient."],
        mitigation: "Canonical IDs, governed vocabulary, alias management, human review for ambiguity.",
      },
      {
        rank: 5,
        title: "Concurrent model traffic",
        bullets: ["Shared model quotas introduce rate limits, latency, and cost pressure."],
        mitigation: "Backoff, queuing, rate controls, model routing, observability, cost governance.",
      },
    ],
    keyLine: "The most dangerous scaling failure isn't a slow query — it's leaking one client's knowledge into another client's decision.",
  },
  {
    kind: "phases",
    id: "rollout",
    num: "07",
    navLabel: "Rollout",
    title: "How I Would Roll It Out",
    opening: "Launch one trusted workflow, not an enterprise knowledge platform.",
    phases: [
      {
        name: "Phase 1 — Shadow mode",
        badge: "Pilot: 5–10 account teams",
        bullets: [
          "System extracts candidate memory.",
          "System proposes recommendations.",
          "Requires human review.",
          "Records agreement and disagreement.",
          "Goal: identify bad memory-writing behavior, measure retrieval quality, understand recommendation overrides, build trust.",
        ],
      },
      {
        name: "Phase 2 — Assisted mode",
        bullets: ["One-click memory approval.", "Conflict resolution.", "Account briefs.", "Decision capture.", "Account handoff support."],
      },
      {
        name: "Phase 3 — Broader institutional intelligence",
        bullets: [
          "Publisher negotiations.",
          "Placement decisions.",
          "Partner recruitment.",
          "Account transitions.",
          "Commercial history.",
          "Privacy-safe portfolio patterns.",
        ],
      },
    ],
    keyLine: "I would launch creator-renewal decision support, not “enter­prise memory.”",
  },
  {
    kind: "adoption",
    id: "adoption",
    num: "08",
    navLabel: "Adoption",
    title: "Driving Adoption",
    opening: "Account managers should not need to understand agents, embeddings, or knowledge graphs.",
    behaviors: [
      "Tell the system meaningful context naturally.",
      "Review what it proposes to remember.",
      "Correct beliefs when they become stale or wrong.",
    ],
    bullets: [
      "Embed the capability in the account workflow rather than creating another destination tool.",
      "Show provenance so users understand why the system believes something.",
      "Make corrections easy and visible.",
      "Start with high-value decisions where remembered context saves obvious work.",
      "Use early champions and concrete examples rather than broad AI training.",
    ],
    stallSignals: [
      "High memory rejection rate.",
      "High recommendation override rate.",
      "Repeated corrections to the same type of memory.",
      "Account managers reconstructing context manually despite system availability.",
      "Low trust in provenance or recommendation grounding.",
    ],
    keyLine: "The value proposition is not “use our AI.” It is “the context you need for this decision is already here.”",
  },
  {
    kind: "measurement",
    id: "measurement",
    num: "09",
    navLabel: "Measurement",
    title: "How I Would Measure Success",
    opening: "Usage is diagnostic. Business outcomes define success.",
    groups: [
      {
        heading: "Account continuity",
        bullets: [
          "Time for a new account manager to become independently effective.",
          "Time spent reconstructing account history.",
          "Missed context after account-team transitions.",
          "Client questions requiring manual historical research.",
        ],
      },
      {
        heading: "Decision quality",
        bullets: [
          "Repeated failed tactics that prior teams had already learned from.",
          "Recommendation override rate.",
          "Stale knowledge affecting decisions.",
          "Economics of supported creator/partner decisions.",
        ],
      },
      {
        heading: "Revenue protected or created",
        bullets: [
          "Poor renewals avoided.",
          "Better commercial terms negotiated.",
          "Successful patterns reused.",
          "Forgotten commercial history recovered.",
          "Revenue leakage avoided.",
        ],
      },
      {
        heading: "Long-term client outcomes",
        bullets: ["Client retention.", "Expansion.", "Executive satisfaction.", "Strategic continuity."],
      },
    ],
    diagnostic: {
      heading: "Diagnostic AI metrics",
      bullets: [
        "Candidate-memory approval rate.",
        "Rejected-memory rate.",
        "Retrieval precision.",
        "Conflict frequency.",
        "Model fallback rate.",
        "Latency.",
        "Cost per decision.",
      ],
    },
    keyLine: "I would not define success as more chats. I would define it as better decisions with less organizational relearning.",
  },
];

export const PRODUCT_THESIS = {
  heading: "The Product Thesis",
  flow: ["Conversation", "Structured memory", "Governed organizational belief", "Business decision", "Outcome", "Portfolio learning", "Better future decision"],
  quote: "The graph is not the product. The product is making what AP learned yesterday available when someone has to make the next decision tomorrow.",
  final: "Every client engagement makes AP smarter.",
};
