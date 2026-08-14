# AP Intelligence Graph
## Case Study Project Specification — Director of Applied AI Product

### One-line product thesis

**Turn every account-team interaction, partnership decision, and outcome into governed organizational memory that makes Acceleration Partners smarter over time.**

---

## 1. Why this project

Acceleration Partners already has foundational AI capabilities for reporting and task efficiency. The more strategic opportunity is not another reporting agent; it is a product that compounds the value of AP's proprietary operational experience.

AP manages hundreds of client programs. Account teams continuously learn things that are strategically valuable but difficult to capture in conventional systems:

- why a client changed strategy;
- why a publisher was dropped or promoted;
- what commercial terms a creator accepted;
- which negotiation structures worked;
- what measurement concerns invalidated an apparent success;
- which account-team decisions were overridden and why;
- what happened after an intervention;
- which relationship owner knows a partner best;
- which lessons appear repeatedly across comparable programs.

Today, much of that knowledge can live in conversations, notes, spreadsheets, email, Slack, presentations, and the heads of experienced account managers. Traditional reporting systems store **what happened**. CRMs store selected **current fields**. RAG can retrieve **what was written down**.

This product is intended to store and reason over:

> **What AP has learned, how strongly it should believe it, when it was true, why it was believed, what decision it influenced, and what happened afterward.**

The case-study prototype should demonstrate how that institutional memory is created, governed, updated, retrieved, and converted into a better partnership decision.

---

## 2. Working product name

# AP Intelligence Graph

**Subtitle:** The living memory of AP's partnership decisions, relationships, and outcomes.

Alternative names if desired later:

- AP Collective Intelligence
- AP Experience Graph
- AP Memory
- AP Decision Memory

For the prototype, use **AP Intelligence Graph** consistently.

---

## 3. Core demo promise

The live demo should prove five things:

1. **The system learns from normal account-team conversation.**
2. **New memories are structured, governed claims rather than free-form summaries.**
3. **The system can detect contradictions and change its active belief without deleting history.**
4. **The agent can use current client memory plus portfolio-level historical experience to make a better decision.**
5. **The resulting decision and outcome become new evidence that improves future organizational intelligence.**

The memorable end-state should be:

> **Every client engagement makes AP smarter.**

---

## 4. Demo scope

The prototype should stay intentionally narrow enough to build and explain clearly.

### Primary workflow

A Northwind Outfitters account manager is deciding whether and how to renew **Summit Sisters**, an influencer partner.

The system should combine:

- Northwind's supplied campaign data;
- newly learned client strategy from a live conversation;
- a known attribution concern from the campaign history;
- synthetic privacy-safe AP portfolio experience;
- a prior strategy memory that conflicts with the newly learned strategy.

The product then recommends an action, captures the decision, and simulates a future outcome that updates the evidence graph.

### Do not attempt in the prototype

Do not build:

- a generic enterprise knowledge management platform;
- a full CRM;
- autonomous campaign execution;
- production identity and permission management;
- a huge cross-client graph;
- a general-purpose chatbot over all AP data;
- a production recommendation model;
- a complete AgentCore deployment if it jeopardizes demo reliability.

The prototype should show the **product behavior and architecture pattern**, not production scale.

---

## 5. Demo data strategy

Use the supplied Northwind case-study workbook as the current-client data foundation.

Extend it with clearly labeled synthetic data representing AP's historical portfolio experience. This is acceptable for the exercise and is central to the product thesis.

### Northwind data to use

At minimum include:

- Northwind client entity;
- Summit Sisters creator entity;
- prior Summit Sisters campaigns;
- campaign fees;
- attributed revenue;
- clicks;
- promo-code redemptions;
- the unusual campaign where redemptions materially exceed tracked clicks.

The prototype should preserve the important distinction that an attribution anomaly is a **hypothesis or risk**, not a confirmed fact.

### Synthetic AP portfolio layer

Seed approximately:

- 4-6 fictional clients;
- 10-15 creators/publishers;
- 20-40 historical decisions;
- 5-10 account-team members;
- 2-4 portfolio patterns;
- 10-20 relationship memories.

Do not overbuild this. The goal is to demonstrate cross-client learning, not statistical validity.

### Recommended portfolio pattern to seed

Create a synthetic pattern such as:

**Pattern:** Hybrid creator compensation performs better than flat-fee renewal when prior commerce performance is promising but attribution confidence is uncertain.

Example evidence:

- 31 comparable historical renewal decisions;
- 21 positive outcomes;
- flat-fee renewal success rate: 41%;
- hybrid base + performance success rate: 68%;
- strongest conditions:
  - repeated prior performance;
  - new-customer objective;
  - controlled promo-code distribution;
  - verified performance outcome.

Clearly label the numbers as synthetic in the UI or demo notes.

---

## 6. Production-grade memory principles

The prototype should model memory as a **versioned knowledge layer**, not as a vector database full of summaries.

### 6.1 Immutable evidence vs mutable active belief

Raw evidence should be append-only:

- conversations;
- tool outputs;
- campaign records;
- decision records;
- outcome records;
- source metadata.

The active memory layer may change over time, but old beliefs remain available for audit.

Conceptually:

```text
append raw evidence forever
        +
carefully mutate the active belief layer
```

### 6.2 Memory types

Support at least the following memory types.

#### Client / account facts

Examples:

- Northwind's current growth objective is new-customer acquisition.
- Northwind wants to reduce coupon concentration.

#### Relationship memory

Examples:

- Jessica has negotiated with Summit Sisters three times.
- A publisher historically requires premium placement guarantees.

#### Episodic / decision memory

Examples:

- Northwind renewed Summit Sisters using a hybrid compensation structure.
- A comparable apparel client reduced a creator's base fee and added a performance tier.

#### Hypotheses / observations

Examples:

- The May Summit Sisters campaign may have experienced promo-code leakage.
- A placement result may be confounded by BFCM seasonality.

These must not be treated as verified facts.

#### Portfolio patterns

Examples:

- Hybrid creator compensation has been associated with better outcomes in comparable renewal decisions.

Portfolio patterns must have an evidence count and should require stronger governance than client-specific observations.

#### Procedural memory

Optional for the prototype.

Examples:

- High-impact commercial changes require account-owner approval.
- Cross-client raw commercial terms may not be exposed to another client.

---

## 7. Memory claim schema

Every durable memory should be represented as an addressable structured claim.

Suggested schema:

```json
{
  "id": "mem_001",
  "type": "client_preference",
  "subject_type": "client",
  "subject_id": "northwind",
  "predicate": "primary_growth_objective",
  "value": "new_customer_acquisition",
  "scope": {
    "client_id": "northwind"
  },
  "claim_class": "verified_fact",
  "confidence": 0.94,
  "authority_score": 0.90,
  "source": {
    "type": "account_team_statement",
    "source_id": "conversation_123",
    "speaker": "account_director"
  },
  "valid_from": "2026-08-14",
  "valid_to": null,
  "status": "active",
  "supersedes": [],
  "created_at": "2026-08-14T12:00:00Z"
}
```

### Required fields

Every claim should have:

- subject;
- predicate;
- value;
- scope;
- claim class;
- confidence;
- source;
- status;
- validity window;
- provenance;
- version relationship when applicable.

---

## 8. Memory statuses

Support these statuses:

```text
active
superseded
expired
low_confidence
needs_review
rejected
deprecated
```

Normal retrieval should use only active and currently valid memories unless historical context is explicitly requested.

---

## 9. Explicit memory operations

Do not expose a generic `save_memory()` operation.

The memory manager should choose an explicit operation:

```text
CREATE
UPDATE
MERGE
SUPERSEDE
EXPIRE
DEMOTE
PROMOTE
REJECT
REQUEST_HUMAN_REVIEW
```

For the prototype, the most important operations are:

- CREATE
- SUPERSEDE
- PROMOTE
- REJECT
- REQUEST_HUMAN_REVIEW

### Operation rules

**CREATE**  
Use when no material related memory already exists.

**UPDATE**  
Use when the new information refines the same active belief without contradicting it.

**SUPERSEDE**  
Use when the new claim replaces an older active belief.

**MERGE**  
Use when multiple memories describe the same concept and should become one canonical claim.

**EXPIRE**  
Use when the memory is no longer valid due to time, campaign end, contract expiration, or another validity rule.

**REJECT**  
Use when a candidate is too vague, unsupported, sensitive, duplicated, or not useful enough to persist.

**PROMOTE**  
Use when repeated episodic evidence becomes a candidate portfolio-level pattern.

**REQUEST_HUMAN_REVIEW**  
Use for strategic, commercial, legal, compliance, privacy, or high-impact updates.

---

## 10. Memory write pipeline

New memory must not be written directly by the conversational agent.

Use this conceptual pipeline:

```text
Conversation / new evidence
          ↓
Memory extraction model
          ↓
Structured candidate claims
          ↓
Schema validation
          ↓
Retrieve related existing memories
          ↓
Conflict / update decision
          ↓
CREATE / UPDATE / SUPERSEDE / REVIEW / REJECT
          ↓
Human approval where required
          ↓
Canonical memory store
          ↓
Graph/index refresh
```

The prototype UI should visibly expose at least part of this process.

---

## 11. Conflict handling

Every candidate memory should search for related active claims before persistence.

At minimum, compare:

- same subject;
- same predicate;
- same client scope;
- semantic similarity;
- existing active value;
- recency;
- source authority.

### Required demo conflict

Seed this old belief:

```text
Northwind
STRATEGY
Aggressively grow coupon partnerships
Status: active
Valid from: January 2026
```

During the live demo, the user tells the agent:

> Northwind's strategy changed after the executive review. They now want to reduce coupon dependence and prioritize new-customer growth.

The system should detect that the new strategy conflicts with the old strategy and propose:

```text
SUPERSEDE

Old:
Grow coupon partnerships
Jan 2026 – Aug 2026

New:
Reduce coupon dependence
Aug 2026 – present
```

The old memory remains visible in history but is excluded from normal retrieval.

This is one of the most important demo moments.

---

## 12. Source authority

Not all memories are equal.

Use a simple authority hierarchy for the prototype.

Suggested order:

```text
structured system-of-record data
    >
verified client / account-lead statement
    >
approved account-team annotation
    >
repeated portfolio evidence
    >
single historical observation
    >
agent inference
```

A high-confidence model inference should still not automatically outrank verified system data.

---

## 13. Confidence and claim class

At minimum support:

```text
verified_fact
account_preference
historical_observation
decision
outcome
hypothesis
portfolio_pattern
```

Example:

### Verified client objective

```text
Northwind → PRIMARY_GOAL → New customer acquisition

Claim class: verified_fact
Source: account director statement
Confidence: 0.96
Status: active
```

### Attribution concern

```text
Summit Sisters May Campaign
    → POSSIBLE_RISK
    → Promo code leakage

Claim class: hypothesis
Evidence:
1,847 code redemptions
385 tracked clicks

Confidence: 0.61
Status: needs_review
```

The agent must use those differently when generating recommendations.

---

## 14. Episodic experience vs portfolio pattern

Do not globalize one client experience into organizational truth.

A single outcome remains an episodic observation.

Example:

```text
Client A
Creator renewal
Flat fee → Hybrid fee
Outcome → Positive
Evidence count: 1
Status: episodic_only
```

Only repeated evidence should become a candidate broader pattern.

Example:

```text
Pattern:
Hybrid creator compensation performs better when attribution confidence is uncertain.

Evidence count: 31
Positive outcomes: 21
Status: approved_portfolio_pattern
```

For the demo, the portfolio pattern can be pre-seeded as approved synthetic evidence.

At the end of the demo, adding the Northwind outcome should update:

```text
31 historical cases → 32
```

Do not claim that one additional case materially proves causality. The visual point is that the evidence base compounds.

---

## 15. Retrieval principles

The recommendation agent should not dump the full graph into the prompt.

Retrieval should be filtered and ranked.

### Retrieval filters

Use:

- client scope;
- entity match;
- active status;
- validity window;
- claim type;
- authority;
- recency;
- semantic relevance;
- conflict state.

### Simplified retrieval score

Conceptually:

```text
retrieval_score =
    semantic_similarity
  + entity_match
  + client_scope_match
  + authority_score
  + recency_score
  - stale_penalty
  - conflict_penalty
```

The prototype does not need a sophisticated learned ranker. A deterministic weighted function is sufficient.

### Retrieval output

The context builder should produce a compact evidence brief such as:

```text
TRUSTED CLIENT MEMORY
- Northwind prioritizes new-customer acquisition.
- Northwind wants to reduce coupon dependence.

CURRENT PARTNER DATA
- Summit Sisters has prior attributed commerce performance.
- The May campaign shows an unusual redemption-to-click relationship.

PORTFOLIO EXPERIENCE
- 31 comparable creator-renewal decisions.
- Hybrid compensation has stronger synthetic historical outcomes than flat-fee renewal.

CAUTION
- Possible promo-code leakage is an unverified hypothesis.
```

---

## 16. Knowledge graph model

The graph should visually represent both entities and knowledge.

### Core entity nodes

Support:

- Client
- Creator
- Publisher
- Campaign
- AccountTeamMember
- Decision
- Outcome
- MemoryClaim
- PortfolioPattern

### Recommended relationships

Use relationships such as:

```text
MANAGES
WORKED_WITH
HAS_CAMPAIGN
HAS_GOAL
HAS_STRATEGY
HAS_RISK
PROPOSED_TERMS
MADE_DECISION
MOTIVATED_BY
RESULTED_IN
SUPPORTS
CONTRADICTS
SUPERSEDES
APPLIES_TO
PROMOTED_TO_PATTERN
```

### Example graph

```text
Northwind
   │
   ├── HAS_GOAL ─────────────> New customer acquisition
   │
   ├── HAS_STRATEGY ─────────> Reduce coupon dependence
   │
   └── MADE_DECISION ────────> Creator Renewal #1038
                                    │
                                    ├── APPLIES_TO ──> Summit Sisters
                                    ├── MOTIVATED_BY ─> Attribution concern
                                    └── RESULTED_IN ──> Outcome #762
```

### Graph visualization

Use a visually dynamic graph library in the frontend.

Good options:

- React Flow;
- Cytoscape.js;
- Sigma.js.

Prefer React Flow for build speed unless the coding agent strongly prefers another library.

The graph should update without a full page refresh.

---

## 17. Primary product interface

Build a single-page demo application with three major regions.

### Left panel — Agent conversation

Shows:

- user messages;
- agent responses;
- business question;
- memory extraction events.

Suggested width: ~30%.

### Center — Live intelligence graph

Shows:

- current client;
- creators/publishers;
- active memories;
- historical/superseded memories;
- decisions;
- outcomes;
- portfolio pattern.

Suggested width: ~45%.

### Right panel — Memory inspector / activity

Shows selected node metadata:

- claim;
- source;
- confidence;
- authority;
- status;
- valid dates;
- evidence;
- supersedes / superseded by.

Also show a compact live activity feed:

```text
09:41 CREATE
Northwind primary objective:
New customer acquisition

09:42 SUPERSEDE
Grow coupon partnerships
→ Reduce coupon dependence

09:43 CREATE
Summit Sisters attribution risk
Status: hypothesis

09:46 DECISION
Hybrid renewal structure approved
```

Suggested width: ~25%.

---

## 18. Candidate memory review interaction

When the extractor finds useful memories, do not silently persist them.

Show a review card:

```text
I found 3 potentially useful memories.

✓ Northwind prioritizes new-customer acquisition
✓ Northwind wants to reduce coupon dependence
⚠ Summit Sisters may have promo-code attribution risk

[Approve all] [Review individually]
```

For each memory show:

- memory type;
- proposed claim;
- source;
- confidence;
- proposed operation.

This is an important trust and governance feature.

---

## 19. Live demo narrative

The demo should be rehearsed around six scenes.

### Scene 1 — Bring me up to speed

User asks:

> Bring me up to speed on Northwind.

The agent retrieves the currently active memories and relevant structured client data.

Important behavior:

- the old coupon-growth strategy is currently active at this point;
- superseded or expired memories should not appear;
- the response should be concise.

Purpose:

Demonstrate retrieval from organizational memory.

### Scene 2 — Teach the system something new

User enters:

> Northwind's strategy changed after last week's executive review. They now want to reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS is a little lower.

The extraction model proposes structured memories:

```text
Northwind → STRATEGY → Reduce coupon dependence
Northwind → PRIMARY_GOAL → New-customer acquisition
Northwind → ACCEPTS_TRADEOFF → Lower short-term ROAS
```

The UI shows them as candidate memories.

The user approves.

Purpose:

Demonstrate natural-language memory creation.

### Scene 3 — Detect and resolve the contradiction

The system recognizes that:

```text
Existing:
Northwind → STRATEGY → Grow coupon partnerships

New:
Northwind → STRATEGY → Reduce coupon dependence
```

Show a conflict dialog.

Proposed action:

```text
SUPERSEDE
```

The user approves.

The old node becomes historical / visually muted.

The new strategy becomes active.

Purpose:

Demonstrate production-grade memory lifecycle management.

Key narration:

> The system can change its mind without forgetting its history.

### Scene 4 — Ask a consequential business question

User asks:

> Summit Sisters wants $6,000 for another campaign. Should we renew them?

The agent retrieves:

#### Client memory

- Northwind prioritizes new customers.
- Northwind wants less coupon dependency.
- Northwind accepts some lower short-term ROAS.

#### Campaign evidence

- Summit Sisters historical performance.
- unusual redemption-to-click behavior in the strongest campaign.

#### Portfolio experience

- synthetic historical pattern around hybrid compensation.

The recommendation should be something like:

```text
RECOMMENDATION
Renegotiate and test.

Suggested structure:
$3,500 base fee
+ performance incentive tied to verified new-customer revenue

Why:
- Northwind's current objective is new-customer acquisition.
- Summit Sisters has promising prior commerce performance.
- The strongest prior result has unresolved attribution quality.
- Comparable synthetic AP portfolio decisions performed better under hybrid compensation.

Confidence:
Moderate

Important uncertainty:
Promo-code leakage is a hypothesis, not a verified fact.
```

Purpose:

Demonstrate that memory changes a real decision.

### Scene 5 — Capture the decision

The user clicks:

**Accept recommendation**

Create a durable decision node:

```text
Decision #NW-1038

Client:
Northwind

Partner:
Summit Sisters

Decision:
Renew under hybrid compensation

Terms:
$3,500 base
+ 10% performance bonus on verified new-customer revenue

Rationale:
- new-customer growth priority
- attribution uncertainty
- portfolio evidence

Status:
Approved

Outcome:
Pending
```

Add graph edges:

```text
Northwind → MADE_DECISION → Decision #NW-1038
Decision #NW-1038 → APPLIES_TO → Summit Sisters
Decision #NW-1038 → MOTIVATED_BY → relevant memories
```

Purpose:

Demonstrate that AP captures not only what happened, but why.

### Scene 6 — Simulate the future outcome

Use an explicitly labeled control:

**Simulate future outcome**

Example synthetic result:

```text
Verified new-customer revenue: $21,400
Attributed revenue: $29,800
Promo-code integrity: clean
Contribution target: exceeded
Outcome: positive
```

Create the outcome node.

Update the synthetic portfolio pattern:

```text
Evidence count:
31 → 32
```

Highlight the new graph path.

Purpose:

Demonstrate the learning loop.

End the demo with:

> Every decision and outcome becomes part of AP's future institutional intelligence.

---

## 20. Recommendation agent behavior

The recommendation agent should use retrieved memory but must distinguish evidence strength.

It should not treat all context equally.

### The prompt should instruct it to

- use verified client preferences as trusted context;
- use structured performance data as trusted observed data;
- treat hypotheses as uncertain;
- explicitly call out conflicting or low-confidence evidence;
- never convert attributed revenue into causal incrementality unless the data supports it;
- use portfolio patterns as supporting evidence, not universal truth;
- produce a structured recommendation;
- cite which memory claims influenced the decision;
- avoid inventing unavailable metrics.

### Suggested structured output

```json
{
  "recommendation": "renegotiate_and_test",
  "recommended_terms": {
    "base_fee": 3500,
    "performance_bonus_pct": 10,
    "bonus_basis": "verified_new_customer_revenue"
  },
  "confidence": 0.74,
  "supporting_memory_ids": [
    "mem_goal_001",
    "mem_strategy_002",
    "mem_risk_003",
    "pattern_hybrid_001"
  ],
  "uncertainties": [
    "Promo-code leakage is suspected but not verified."
  ],
  "explanation": "..."
}
```

---

## 21. Agent responsibilities

Use separate logical responsibilities even if the prototype implements them with one model provider.

### Memory extraction agent

Input:

- new conversation message;
- current entity context.

Output:

- candidate structured claims.

It should not write to the database.

### Memory conflict manager

Input:

- candidate claim;
- related existing claims.

Output:

- one explicit memory operation.

Prefer deterministic same-subject + same-predicate checks before invoking the model.

### Recommendation agent

Input:

- user question;
- compact retrieved context;
- structured client/campaign data.

Output:

- structured recommendation;
- supporting memory IDs;
- uncertainty;
- confidence.

### Pattern promotion logic

For the prototype, keep promotion mostly deterministic.

Example:

- minimum evidence count;
- sufficient outcome consistency;
- no unresolved privacy issue;
- human approval required.

The demo can use a pre-seeded approved pattern rather than asking the LLM to infer a new pattern from scratch.

---

## 22. Deterministic logic vs LLM logic

The LLM should not own everything.

### Deterministic code should handle

- schema validation;
- IDs;
- timestamps;
- active/superseded state transitions;
- validity windows;
- same-subject + same-predicate conflict lookup;
- source authority rules;
- retrieval filtering;
- graph persistence;
- cross-client isolation;
- outcome counts;
- memory operation execution;
- permissions in the production design.

### LLM should handle

- extracting candidate claims from natural language;
- classifying claim type;
- suggesting whether a new statement refines or contradicts an existing belief;
- synthesizing retrieved evidence;
- explaining recommendations;
- generating concise decision rationales.

Key principle:

> The model proposes; application logic validates and persists.

---

## 23. Prototype technology stack

Prioritize reliability and build speed.

### Frontend

- Next.js
- TypeScript
- React
- React Flow for graph visualization

### Backend

Preferred:

- Python
- FastAPI
- Pydantic

### Prototype data store

Choose the simplest reliable option:

**Preferred:** SQLite or local PostgreSQL.

Use relational tables for canonical memory and edge records. A dedicated graph database is not required for the demo.

Suggested tables:

```text
clients
partners
campaigns
team_members
memory_claims
memory_edges
decisions
outcomes
portfolio_patterns
raw_events
```

### Semantic retrieval

Optional for MVP.

If time allows:

- store embeddings for claim text;
- use pgvector if using PostgreSQL;
- otherwise use a lightweight in-memory similarity layer.

The prototype can work primarily through:

- entity filters;
- predicate filters;
- status filters;
- client scope;
- deterministic keyword / simple semantic retrieval.

Do not jeopardize the demo trying to perfect vector search.

### LLM provider

Implement a provider interface.

Possible providers:

- OpenAI API for demo simplicity;
- Amazon Bedrock if credentials are readily available.

The architecture should remain provider-agnostic.

---

## 24. Suggested backend API

Keep the API small.

### Account context

```http
GET /api/clients/{client_id}/brief
```

Returns current active memory + structured client summary.

### Graph

```http
GET /api/clients/{client_id}/graph
```

Returns nodes and edges.

### Chat

```http
POST /api/chat
```

Input:

```json
{
  "client_id": "northwind",
  "message": "..."
}
```

Output may contain:

- assistant response;
- candidate memories;
- relevant memory IDs.

### Approve memories

```http
POST /api/memories/review
```

Input:

```json
{
  "candidate_id": "...",
  "action": "approve"
}
```

### Resolve conflict

```http
POST /api/memories/conflicts/{conflict_id}/resolve
```

Input:

```json
{
  "operation": "SUPERSEDE"
}
```

### Recommendation

```http
POST /api/recommendations
```

Input:

```json
{
  "client_id": "northwind",
  "partner_id": "summit_sisters",
  "question": "Should we renew at $6,000?"
}
```

### Accept decision

```http
POST /api/decisions
```

### Simulate outcome

```http
POST /api/decisions/{decision_id}/simulate-outcome
```

Clearly label this endpoint and UI control as demo-only.

---

## 25. Suggested folder structure

```text
ap-intelligence-graph/
│
├── frontend/
│   ├── app/
│   ├── components/
│   │   ├── ChatPanel.tsx
│   │   ├── IntelligenceGraph.tsx
│   │   ├── MemoryInspector.tsx
│   │   ├── CandidateMemoryReview.tsx
│   │   ├── ConflictDialog.tsx
│   │   ├── RecommendationCard.tsx
│   │   └── ActivityFeed.tsx
│   └── lib/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── db.py
│   │   ├── seed.py
│   │   │
│   │   ├── agents/
│   │   │   ├── memory_extractor.py
│   │   │   ├── recommendation_agent.py
│   │   │   └── prompts/
│   │   │
│   │   ├── memory/
│   │   │   ├── manager.py
│   │   │   ├── conflict_resolver.py
│   │   │   ├── retrieval.py
│   │   │   ├── scoring.py
│   │   │   └── operations.py
│   │   │
│   │   └── routers/
│   │       ├── chat.py
│   │       ├── memory.py
│   │       ├── graph.py
│   │       ├── recommendations.py
│   │       └── decisions.py
│   │
│   └── data/
│       ├── northwind_seed.json
│       ├── synthetic_portfolio.json
│       └── demo_outcome.json
│
├── PROJECT.md
└── README.md
```

---

## 26. Seed memories required for the demo

At minimum seed these memories.

### Old strategy

```text
Subject: Northwind
Predicate: partnership_strategy
Value: aggressively_grow_coupon_partnerships
Status: active
Valid from: 2026-01-01
```

### Summit Sisters relationship

```text
Subject: Summit Sisters
Predicate: relationship_status
Value: existing_creator_partner
Status: active
```

### Attribution hypothesis

This can either be seeded or generated deterministically from supplied campaign data.

```text
Subject: Summit Sisters May Campaign
Predicate: attribution_integrity_risk
Value: possible_promo_code_leakage
Claim class: hypothesis
Confidence: 0.61
Status: needs_review
```

### Portfolio pattern

```text
Subject: comparable_creator_renewals
Predicate: preferred_compensation_pattern
Value: hybrid_base_plus_performance
Evidence count: 31
Status: active
Scope: privacy_safe_portfolio
```

---

## 27. Visual language

The UI should feel like an enterprise intelligence product, not a sci-fi demo.

### Graph visual semantics

Use visual distinctions for:

- entity nodes;
- active memory;
- hypothesis;
- superseded memory;
- decision;
- outcome;
- portfolio pattern.

Do not rely only on color. Also use:

- labels;
- icons;
- borders;
- status badges;
- opacity for historical nodes.

### Important interaction

When a new memory is approved:

- animate node creation;
- animate relationship connection;
- add activity-feed entry.

When a memory is superseded:

- keep the old node;
- mark it historical;
- visually connect `SUPERSEDES`.

When a recommendation is generated:

- highlight the memory nodes used as evidence.

This is the primary visual "wow" moment.

---

## 28. Production architecture story

The prototype may run locally, but the presentation should explain a credible AWS production path.

### Conceptual AWS architecture

```text
Existing APVision / internal app
            │
            ▼
      API Gateway / app API
            │
            ▼
     Application services
            │
      ┌─────┴─────────┐
      │               │
      ▼               ▼
AgentCore Runtime   Memory Manager
      │               │
      ▼               ▼
Bedrock model     Canonical memory store
                      │
             ┌────────┴────────┐
             ▼                 ▼
      semantic index       graph layer
             │                 │
             └────────┬────────┘
                      ▼
                retrieval layer
                      │
                      ▼
               recommendation agent
```

### Likely AWS components

Possible production choices:

- **AgentCore Runtime** for agent execution;
- **Amazon Bedrock** for foundation models;
- **Aurora PostgreSQL** for canonical structured memory;
- **pgvector / OpenSearch** for semantic retrieval;
- **Neptune** if graph traversal complexity justifies a dedicated graph store;
- **S3** for immutable raw evidence and evaluation artifacts;
- **Step Functions / EventBridge** for asynchronous consolidation, review, expiration, and promotion workflows;
- **CloudWatch** for observability;
- **IAM / KMS** for identity, authorization, and encryption.

Do not claim Neptune is mandatory. Start with relational graph tables unless scale or traversal requirements justify it.

---

## 29. Cross-client privacy model

The product's strategic value depends on cross-client learning, but raw client data must remain isolated.

Model three levels of knowledge:

```text
CLIENT-PRIVATE MEMORY
specific client facts, strategy, terms, notes
          ↓
AP INTERNAL OPERATING MEMORY
relationship ownership, internal process knowledge
          ↓
PRIVACY-SAFE PORTFOLIO INTELLIGENCE
aggregated patterns, model outputs, benchmark insights
```

### Example

Another client may **not** retrieve:

> Northwind paid Summit Sisters $3,500.

Another client may retrieve:

> Comparable outdoor/apparel creator renewals with uncertain attribution have historically performed better under hybrid compensation structures.

For the demo, cross-client privacy is simulated through scope fields and filtered retrieval.

---

## 30. What is real vs stubbed in the prototype

Be explicit in the presentation.

### Real

The prototype should genuinely perform:

- natural-language memory extraction;
- schema validation;
- candidate memory review;
- conflict detection;
- supersession;
- graph update;
- active-memory retrieval;
- evidence-aware recommendation generation;
- decision capture;
- outcome insertion;
- portfolio evidence-count update.

### Stubbed / simplified

Be honest that these are simplified:

- enterprise SSO;
- production RBAC;
- real APVision integrations;
- real cross-client portfolio data;
- production AgentCore deployment if not used in the prototype;
- high-scale graph infrastructure;
- sophisticated semantic retrieval;
- automated background pattern discovery;
- causal claims from historical portfolio data;
- production privacy review;
- model evaluation at scale.

---

## 31. What breaks first at 200+ clients

Prepare for this question.

### Memory pollution

Too many low-value claims can degrade retrieval.

Mitigation:

- strict write rules;
- candidate review;
- memory types;
- retention policies;
- promotion/demotion logic.

### Stale memory

Client goals, contracts, strategies, and relationships change.

Mitigation:

- validity windows;
- conflict detection;
- source authority;
- explicit supersession;
- review dates.

### Contradictory memories

Different account-team members may provide conflicting statements.

Mitigation:

- source authority;
- active vs needs-review state;
- conflict queue;
- human verification.

### Entity resolution

Names can be inconsistent across networks and tools.

Mitigation:

- canonical IDs;
- alias tables;
- deterministic entity-resolution layer;
- human review for ambiguous matches.

### Cross-client leakage

Portfolio retrieval may accidentally expose client-specific information.

Mitigation:

- hard tenant filters before model access;
- privacy-safe aggregation layer;
- scope enforcement in code;
- audit logs.

### Over-generalization

The system may promote anecdotes into global "truth."

Mitigation:

- episodic vs pattern distinction;
- minimum evidence thresholds;
- human approval;
- outcome quality weighting;
- causal-strength metadata.

### Graph explosion

Every raw event should not become a node.

Mitigation:

- graph contains meaningful entities, claims, decisions, and outcomes;
- raw evidence stays outside the graph;
- summarization/consolidation jobs.

### User trust

Account managers will abandon the tool if they cannot understand why the system "remembers" something.

Mitigation:

- visible provenance;
- confidence labels;
- memory review;
- explanation of supersession;
- source links.

---

## 32. Rollout strategy

The case brief specifically cares about adoption by non-technical account teams.

Do not launch this as "enterprise memory."

Launch it around one useful workflow.

### Pilot workflow

**Creator renewal memory + decision support**

Pilot with approximately 5-10 account teams.

### Phase 1 — Shadow mode

The system:

- extracts candidate memory;
- does not change active memory without approval;
- recommends decisions;
- records user agreement/disagreement.

Goal:

Build trust and identify bad memory-writing behavior.

### Phase 2 — Assisted mode

Allow:

- one-click memory approval;
- conflict resolution;
- decision capture;
- account handoff briefs.

### Phase 3 — Broader institutional memory

Add:

- publisher negotiation memory;
- partner recruitment history;
- placement decisions;
- account transitions;
- privacy-safe portfolio patterns.

### Enablement

Account managers should not need to understand graphs or embeddings.

Train them on three behaviors:

1. Tell the agent meaningful context naturally.
2. Review proposed memories.
3. Correct the system when its belief is stale or wrong.

---

## 33. Business success metrics

Do not present usage as the primary success definition.

### Account continuity

Measure:

- time required for a new account manager to become independently effective after a handoff;
- reduction in missed context after account-team turnover;
- reduction in client questions that require historical reconstruction.

### Decision quality

Measure:

- rate of repeated failed tactics that prior AP teams had already learned from;
- economic outcome of supported creator / placement / commission decisions;
- frequency with which stale or incorrect institutional knowledge changes a decision.

### Revenue protected / created

Measure:

- value protected from avoided poor renewals;
- incremental value from reused successful partnership patterns;
- reduced commercial leakage from forgotten historical terms;
- client expansion influenced by surfaced portfolio opportunities.

### Client retention

Longer term:

- renewal and retention differences for accounts using the system;
- executive satisfaction with strategic continuity.

### Operational metrics

Use only diagnostically:

- memory approval rate;
- conflict frequency;
- rejected-memory rate;
- retrieval precision;
- recommendation override rate;
- latency;
- cost per interaction.

---

## 34. Evaluation framework

The memory system should be evaluated separately from the conversational quality.

### Memory extraction accuracy

For a small labeled test set:

- did it identify the correct subject?
- correct predicate?
- correct value?
- correct claim type?
- correct scope?
- did it avoid saving irrelevant chatter?

### Conflict-resolution accuracy

Test:

- same fact repeated;
- same fact refined;
- fact contradicted;
- old fact expired;
- low-authority contradiction;
- client-specific vs portfolio-wide claim.

### Retrieval quality

Measure whether retrieved context is:

- relevant;
- current;
- appropriately scoped;
- authoritative;
- compact.

### Recommendation grounding

Check that:

- every major recommendation is supported by retrieved evidence;
- hypotheses are labeled as uncertain;
- the model does not invent unavailable metrics;
- superseded memory is not treated as current.

---

## 35. MVP acceptance criteria

The build is demo-ready when all of the following work.

- [ ] Northwind loads with seeded client, creator, campaign, and memory data.
- [ ] The graph renders and can inspect node metadata.
- [ ] `Bring me up to speed on Northwind` retrieves active memory.
- [ ] A natural-language strategy update generates candidate structured memories.
- [ ] The user can approve candidate memories.
- [ ] The system detects the old coupon-strategy conflict.
- [ ] The system can `SUPERSEDE` the old strategy.
- [ ] The old memory remains visible as historical.
- [ ] Normal retrieval excludes the superseded strategy.
- [ ] The Summit Sisters attribution issue is stored as a hypothesis, not a fact.
- [ ] The user can ask whether to renew Summit Sisters at $6,000.
- [ ] The recommendation uses current client memory + portfolio evidence.
- [ ] The recommendation visibly identifies supporting memory nodes.
- [ ] The user can accept the recommendation.
- [ ] Accepting creates a durable Decision node.
- [ ] `Simulate future outcome` creates an Outcome node.
- [ ] The synthetic portfolio pattern evidence count increments.
- [ ] The graph updates without page refresh.
- [ ] All synthetic cross-client data is clearly labeled as synthetic.

---

## 36. Recommended build order

The coding agent should optimize for a reliable live demo.

### Step 1 — Data model and seed

Build:

- memory claim schema;
- graph edge schema;
- Northwind seed data;
- synthetic portfolio data.

### Step 2 — Static graph UI

Render:

- Northwind;
- Summit Sisters;
- old coupon strategy;
- portfolio pattern;
- campaign node.

Make node inspection work.

### Step 3 — Memory extraction

Add:

- chat input;
- LLM extraction;
- structured candidate output;
- review card.

### Step 4 — Conflict engine

Implement:

- same subject + predicate lookup;
- supersede operation;
- validity update;
- graph visual change.

### Step 5 — Retrieval + recommendation

Implement:

- active memory retrieval;
- compact context builder;
- Summit Sisters recommendation;
- evidence highlighting.

### Step 6 — Decision + outcome loop

Implement:

- accept recommendation;
- decision node;
- simulated outcome;
- evidence count update.

### Step 7 — Polish only if time remains

Add:

- smooth graph animations;
- activity feed;
- better metadata inspector;
- loading states;
- error states.

Do not sacrifice workflow correctness for visual polish.

---

## 37. Presentation framing

The presentation should avoid starting with architecture.

Start with the business problem:

> AP already knows how to report on what happened. The harder question is whether the organization can remember why teams made decisions, how circumstances changed, and what was learned across hundreds of programs.

Then state the thesis:

> I built a prototype of a governed institutional memory layer that learns from normal account-team interactions and makes that experience available at the moment of the next decision.

Then go directly to the live demo.

After the demo, explain:

1. why the workflow matters;
2. production memory principles;
3. what is real vs stubbed;
4. how it would scale in AWS / AgentCore;
5. adoption;
6. business measurement.

---

## 38. Key lines to use in the presentation

These are useful framing statements, not UI copy.

> **The system can change its mind without forgetting its history.**

> **A model inference and a verified client statement should never have equal authority.**

> **One successful campaign is an episode; repeated evidence can become institutional knowledge.**

> **The model proposes memory, but governed application logic decides what persists.**

> **The graph is not the product by itself. The value is that the next account team can act on what the last account team learned.**

> **The strategic asset is not more chat history. It is structured decision-and-outcome memory across hundreds of programs.**

> **Every client engagement makes AP smarter.**

---

## 39. Longer-term product roadmap

The case-study prototype should focus on creator renewal, but the memory layer can power several future products.

### Relationship intelligence

Ask:

> Who at AP has worked with this partner, what did we negotiate, and what should I know before outreach?

### Account handoff

Ask:

> Bring me up to speed on the five decisions that matter most for this client.

### Partner recruitment

Ask:

> Have we recruited similar publishers for comparable clients, and what drove successful activation?

### Commercial deal desk

Ask:

> What terms have similar partners accepted, and what should we offer?

### Experiment memory

Ask:

> Have we tested this intervention before, under what conditions, and what happened?

### Portfolio learning

Ask:

> What patterns are emerging across creator renewals, commission changes, placements, or partner recruitment?

### Next-best action

Eventually:

> Given this client's current context and AP's accumulated experience, what should the account team do next?

The long-term progression is:

```text
Memory
   ↓
Institutional intelligence
   ↓
Prediction
   ↓
Decision advantage
```

---

## 40. Final product thesis

AP's defensible AI advantage is unlikely to come from having more agents that summarize reports.

It can come from converting the experience generated across hundreds of client programs into a governed learning system.

The prototype should demonstrate that progression in miniature:

```text
Conversation
     ↓
Structured memory
     ↓
Conflict resolution
     ↓
Current organizational belief
     ↓
Business decision
     ↓
Outcome
     ↓
Portfolio learning
     ↓
Better future decision
```

**That loop is the product.**
