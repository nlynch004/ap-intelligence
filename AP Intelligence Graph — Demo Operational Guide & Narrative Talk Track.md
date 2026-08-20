# AP Intelligence
## Demo Operational Guide & Narrative Talk Track

**Purpose:** Director of Applied AI Product Case Study  
**Primary workflow:** Northwind Outfitters creator-renewal decision support  
**Primary partner:** Summit Sisters  
**Demo thesis:** **Every client engagement makes AP smarter.**

---

# 1. What the demo is proving

The demo is not intended to prove that an LLM can calculate ROAS or summarize campaign performance.

The workflow is designed to demonstrate something harder:

> AP account teams continuously learn strategic information that affects future decisions, but much of that knowledge lives in conversations, notes, spreadsheets, and people's heads rather than in structured systems.

The prototype turns that information into governed organizational memory and uses it at the moment of a consequential business decision.

The complete loop is:

```text
Account-team conversation
        ↓
Candidate structured memory
        ↓
Validation + conflict detection
        ↓
Human review
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

The product specification's core promise is that the system can learn from normal account-team interactions, preserve provenance and uncertainty, change active beliefs without deleting history, use both current-client and portfolio experience in a decision, and then turn the resulting decision/outcome into future evidence.

---

# 2. Recommended presentation arc

The case-study session gives approximately 30 minutes for presentation followed by questions.

Use roughly:

### 0–4 minutes
**Problem, workflow choice, and why AI belongs here**

### 4–16 minutes
**Live six-scene demo**

### 16–21 minutes
**What's real vs simplified**

### 21–25 minutes
**What breaks at 200+ clients / production architecture**

### 25–30 minutes
**Rollout and business measurement**

Do not spend the first five minutes explaining the graph schema or AWS architecture.

The business decision comes first.

---

# 3. Before the interview

## Backend

Open Terminal 1:

```bash
cd /Users/nicklynch/Documents/Projects/ap_intelligence/ap-intelligence-graph/backend
uv run uvicorn app.main:app --port 8000
```

Expected backend:

```text
http://localhost:8000
```

Required:

```text
backend/.env
OPENAI_API_KEY=...
```

---

## Frontend

Open Terminal 2:

```bash
cd /Users/nicklynch/Documents/Projects/ap_intelligence/ap-intelligence-graph/frontend
npm run dev
```

Expected frontend:

```text
http://localhost:3000
```

Required:

```text
frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Health check

Run:

```bash
curl -s http://localhost:8000/api/health
```

Expected:

```json
{
  "status": "ok",
  "llm_provider": "openai"
}
```

If you see:

```text
mock_deterministic
```

instead of:

```text
openai
```

check the backend `.env` and restart the backend.

The app does have a deterministic model fallback, but you want the interview demo using the live OpenAI provider.

---

# 4. Reset before every rehearsal

In the application header:

**Reset demo (demo only)**

Click:

**Reset demo**

Then:

**Yes, reset**

The reset has been verified to restore:

```text
Graph:
11 nodes
15 edges

Northwind strategy:
aggressively_grow_coupon_partnerships
status = active
valid_to = null

Portfolio pattern:
evidence_count = 31
positive_outcomes = 21

Decisions:
0

Outcomes:
0

Pending candidates:
0

Activity:
2 seeded events
```

The reset is idempotent, so running it twice produces the same canonical state.

---

# 5. Opening visual inspection

Before screen sharing, verify:

- Northwind loads.
- Right panel defaults to **Northwind Outfitters**.
- Portfolio pattern visibly displays **SYNTHETIC**.
- Campaign labels are readable, such as:

```text
Summit Sisters
May 2026 Campaign
```

- Summit Sisters and Trail With Tessa May campaigns are visually distinguishable.
- Graph is at a comfortable zoom.
- Browser notifications are disabled.
- Only the app tab you need is visible.

Do not start the interview by showing terminals.

---

# 6. Opening narrative — approximately 3–4 minutes

## Start with the business problem

Say:

> “I focused on one account-team decision: Summit Sisters wants $6,000 for another creator campaign. Should Northwind renew them, and if so, under what commercial structure?”

Then explain why this isn't just a ROAS-ranking exercise:

> “The interesting part isn't calculating historical performance. That's deterministic analytics. The difficult part is that the right answer also depends on what the client currently cares about, whether we trust the historical attribution, what AP has learned from comparable decisions, and whether any of that context has changed since the last time we worked on the account.”

Then introduce the data signal.

### Summit Sisters history

The application uses:

```text
September 2025
Fee: $4,000
Attributed revenue: $9,840
Attributed ROAS: 2.46x
Clicks: 880
Code redemptions: 255

February 2026
Fee: $4,000
Attributed revenue: $10,120
Attributed ROAS: 2.53x
Clicks: 905
Code redemptions: 268

May 2026
Fee: $4,200
Attributed revenue: $31,240
Attributed ROAS: 7.44x
Clicks: 385
Code redemptions: 1,847
```

Then say:

> “The first two campaigns are quite consistent. May suddenly looks dramatically better commercially, but it also has 1,847 code redemptions against only 385 tracked link clicks. That doesn't prove promo-code leakage, but it means I don't want the system treating the apparent 7.4x ROAS as unquestioned truth.”

Then introduce the strategic problem:

> “And there's a second challenge: client strategy itself changes. A historical dashboard can tell me what happened, but it doesn't necessarily know that the executive team changed its priorities last week.”

---

# 7. Why you chose this workflow

Say:

> “I deliberately didn't build another reporting agent. AP already has structured performance data. I wanted to focus on the gap between reporting and decision-making: capturing what the account team learns and making that knowledge available when the next consequential decision happens.”

If you want to explain alternatives:

### Alternative considered: creator ranking

> “I could have ranked creators by attributed ROAS. But SQL can do most of that. AI doesn't add much differentiated value.”

### Alternative considered: placement optimization

> “I also considered optimizing affiliate placements, but the supplied data doesn't give me enough counterfactual evidence to claim causal incrementality, particularly around seasonal events like BFCM.”

### Chosen workflow

> “Creator-renewal decision support sits in a much more interesting space because it combines structured performance data, changing strategy, ambiguous measurement, human knowledge, and organizational experience.”

---

# 8. Transition into the live demo

Say:

> “So rather than starting with architecture, I'll show you the workflow from the perspective of an account manager.”

Then move directly into Scene 1.

---

# SCENE 1 — Bring me up to speed

## User action

Use the suggested prompt or enter:

```text
Bring me up to speed on Northwind.
```

## Expected latency

Approximately:

```text
0.7–1.0 seconds
```

Measured mean:

```text
870 ms
```

across the three final live-model runs.

## What you should see

The agent should summarize current active Northwind context.

At this point, the old strategy is intentionally still current:

```text
Aggressively grow coupon partnerships
```

It should not retrieve superseded or expired memory because none has been changed yet.

---

## Talk track while it loads

> “The first thing I'm doing is asking the system for the account's current state.”

When the response appears:

> “Notice that the coupon-growth strategy is still present. That's intentional. Right now, according to institutional memory, that's what AP believes.”

Then:

> “This isn't dumping all historical notes into the prompt. Retrieval filters for current, relevant, appropriately scoped memory.”

---

## What this scene proves

### Technically

```text
ChatPanel
   ↓
POST /api/chat
   ↓
active_client_memories()
   ↓
SQLite memory_claims
   ↓
LLM summarization
```

The LLM is being used for concise synthesis.

The underlying active-memory selection is deterministic.

---

## Exact backend input / output contract

**Input sent to the model** — deliberately compact, and only `predicate`/`value` pairs, nothing else:

```text
active_client_memories(db, client_id)
  → [{"predicate": "partnership_strategy", "value": "aggressively_grow_coupon_partnerships"}, ...]
```

No ids, confidence, source, or timestamps are sent. This is also the one call in the whole app that isn't asked for JSON — the system prompt lives inline in `OpenAIProvider.summarize()`, not in `agents/prompts.py` with everything else:

> "You write brief, concrete account-status summaries for AP account managers. 2-4 sentences, no fluff."

User prompt:

```text
Client: Northwind Outfitters
Active memory:
- partnership_strategy: aggressively_grow_coupon_partnerships
- relationship_status: ...

Summarize what AP currently knows about this client.
```

**What the model is asked to produce:** plain prose, not structured JSON — the only exception to the "everything is validated JSON" rule elsewhere in the app.

**How the output is generated:** the string comes back as `ChatResponse.reply` verbatim — no schema, no computed fields, nothing to validate. Because there's no JSON to malform, there's also no `RawXOut` validator or fallback-on-invalid-shape step here; the only failure mode is the call itself erroring, in which case `call_with_fallback` runs the mock provider's own rule-based summarizer (`"- {predicate}: {value}"` per line) instead. `referenced_memory_ids` (which drives the graph highlight) is attached separately from the same `active_client_memories` query — never parsed out of the model's text.

---

## While testing, verify

- Old coupon-growth strategy appears.
- No duplicate strategy.
- No new-customer strategy yet.
- Response is concise.
- Graph does not unexpectedly move.

---

# SCENE 2 — Teach the system something new

## User action

Enter exactly:

```text
Northwind's strategy changed after last week's executive review. They now want to reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS is a little lower.
```

## Expected latency

Approximately:

```text
2 seconds
```

Measured:

```text
Mean: 2.08 sec
Min: 2.00 sec
Max: 2.17 sec
```

This is the longest live-model step.

---

## Talk track while it runs

Use the latency rather than waiting silently:

> “This is where I actually need the language model. The account manager is speaking naturally; they shouldn't have to open a CRM field editor and translate this conversation into an ontology.”

When the candidate card appears:

> “The model has interpreted the conversation, but importantly, it has not changed organizational memory.”

---

## Expected candidates

You should see three candidate claims:

```text
partnership_strategy
→ reduce_coupon_dependence

primary_growth_objective
→ new_customer_acquisition

accepts_tradeoff
→ lower_short_term_roas
```

Each should show:

- proposed claim;
- source;
- confidence;
- claim class;
- proposed operation.

---

## Point to the candidate review

Say:

> “These are proposed memories. The model doesn't get direct write access to canonical memory.”

Then:

> “This is a deliberate trust boundary: the model proposes; application logic validates; a person approves what becomes durable knowledge.”

---

# 9. What is happening technically in Scene 2

The actual pipeline is:

```text
Natural-language statement
        ↓
Memory extraction LLM
        ↓
ExtractedClaimIn
Pydantic validation
        ↓
Canonical predicate normalization
        ↓
Known predicate?
    ↙         ↘
  yes          no
   ↓            ↓
conflict      REQUEST_
lookup        HUMAN_REVIEW
   ↓
pending MemoryCandidate
        ↓
Human approval required
```

Important interview point:

> “I intentionally kept predicate normalization deterministic rather than asking another LLM to decide whether two predicates mean roughly the same thing.”

Example:

```text
client_strategy
→ partnership_strategy
```

is handled by a governed alias table.

---

## Exact backend input / output contract

**Input sent to the model:**

```text
client_id: northwind
client_name: Northwind Outfitters
KNOWN PREDICATES for this client (reuse exactly when applicable): partnership_strategy, relationship_status, negotiation_history, attribution_integrity_risk
KNOWN PARTNERS for this client (reuse the id exactly when the message names one of them): summit_sisters: Summit Sisters (creator), peak_pursuit: Peak Pursuit (creator), campfire_kate: Campfire Kate (creator), backcountry_ben: Backcountry Ben (creator), trail_with_tessa: Trail With Tessa (creator)
message: Northwind's strategy changed after last week's executive review. They now want to reduce coupon dependence and prioritize new-customer growth, even if short-term ROAS is a little lower.
```

`known_predicates`/`known_partners` exist for one reason: conflict detection downstream is an **exact-string match**, not semantic. If the model paraphrases a predicate name or invents a new slug for an existing partner, the conflict lookup silently misses it. Feeding back the client's actual current vocabulary steers the model to reuse it.

The system prompt (`EXTRACTION_SYSTEM_PROMPT`, `agents/prompts.py`) spells out, with worked examples: the required field list per claim; a lookup table of which predicate belongs to which `subject_type` (getting this wrong attaches an otherwise-correct claim to the wrong graph entity — e.g. a `relationship_status` claim about a named partner must have `subject_type: "creator"`, never `"client"`, even when the sentence is phrased from the account team's point of view); to split one sentence bundling several facts into separate claims; and to reuse a KNOWN PREDICATES/KNOWN PARTNERS entry verbatim rather than inventing a near-duplicate.

**What the model is asked to produce**, one object per claim, wrapped as `{"claims": [...]}`:

```json
{
  "type": "client_preference",
  "subject_type": "client",
  "subject_id": "northwind",
  "subject_label": "Northwind Outfitters",
  "predicate": "partnership_strategy",
  "value": "reduce_coupon_dependence",
  "claim_class": "verified_fact",
  "confidence": 0.93,
  "rationale": "Account team stated the client's strategy shifted away from coupon growth."
}
```

It is explicitly correct for this to come back as an **empty list** — the prompt tells the model not to force a claim out of vague chatter.

**How each claim becomes governed memory (or doesn't)** — all deterministic, none of it is the model's decision:

```text
raw claim dict (one per extracted claim)
   ↓
ExtractedClaimIn(**raw)            Pydantic validation — malformed/out-of-range dropped, never persisted or shown
   ↓
normalize_predicate(predicate)     deterministic alias table lookup
   ↓
   known predicate? ──no──►  proposed_operation = REQUEST_HUMAN_REVIEW  (skips automatic conflict matching)
   │ yes
   ↓
find_active_conflict(subject_type, subject_id, predicate, client_id)   exact-match DB lookup, not the model's job
   ↓
decide_operation(payload, existing)   → CREATE | UPDATE | SUPERSEDE
   ↓
pending MemoryCandidate row (status = "pending")
```

Nothing below the Pydantic-validation line is written to canonical memory yet, and nothing above it is model-influenced — the model supplies claim *content*; the app decides what operation that content implies and whether it's even a recognized concept.

---

## If asked about semantic errors

Say:

> “Pydantic protects the structure, but it can't guarantee that a structurally valid interpretation is semantically right. That's why high-value memory changes remain human-reviewed before persistence.”

That is the correct safety explanation.

---

## While testing, verify

- Exactly three candidates appear.
- Strategy candidate recognizes existing conflict.
- All candidates remain pending.
- Existing active strategy is still unchanged.
- Source displays properly.
- Candidate review card is readable without excessive scrolling.

---

# SCENE 3 — Approve and resolve contradiction

## User action

Click:

**Approve all**

The strategy candidate should trigger the conflict interaction.

You should see something equivalent to:

```text
Existing:
Aggressively grow coupon partnerships

New:
Reduce coupon dependence
```

Proposed operation:

```text
SUPERSEDE
```

Click:

**Supersede**

---

## Talk track

When the conflict appears:

> “Here's the key memory-management moment. This isn't a duplicate record. The new information contradicts an existing active belief.”

Then:

> “A naive memory system might overwrite the old text or leave both versions active. Instead, this proposes an explicit state transition.”

Click **Supersede**.

Then say:

> “The system can change its mind without forgetting its history.”

Pause and point to the graph.

> “The old strategy remains visible, but it's historical. The new strategy becomes active and normal retrieval will stop treating the old one as current.”

---

# 10. Expected graph behavior

After supersession:

### Old claim

```text
Value:
aggressively_grow_coupon_partnerships

Status:
superseded

valid_to:
set

Visual:
dimmed / historical
```

### New claim

```text
Value:
reduce_coupon_dependence

Status:
active

valid_to:
null
```

The viewport should automatically focus on the old and new strategy nodes.

---

## Technical explanation

Say:

> “The LLM didn't execute the state transition. Conflict lookup, status changes, validity dates, supersession relationships, IDs and persistence are deterministic application logic.”

The system performs:

```text
old.status = superseded
old.valid_to = today

new.status = active
new.supersedes = old.id
```

Old memory remains in the database.

---

## No model call in this step

Worth stating explicitly if asked: clicking **Approve all** and then **Supersede** never calls the LLM. The claim content was already generated back in Scene 2 and is sitting in the `memory_candidates` table with `status = "pending"`; this step only runs `execute_supersede()` (or `execute_create()`/`execute_update()` for the two non-conflicting candidates) — a plain state-transition function operating on data that already exists. Input: the candidate's stored `claim_payload` dict + the existing conflicting claim's row. Output: two updated rows (`old.status/valid_to/superseded_by`, `new` claim inserted with `supersedes: [old.id]`) plus one `ActivityEvent` and the matching graph edges (`SUPERSEDES`, and a `HAS_STRATEGY`/`HAS_GOAL`/etc. edge from the client to the new claim). If a live audience asks "what does the model do when I click Supersede," the honest answer is: nothing — it already did its job upstream, in Scene 2.

---

## Optional verification

If you want to prove it live, ask again:

```text
Bring me up to speed on Northwind.
```

You should now see:

- reduce coupon dependence;
- prioritize new-customer acquisition;

and not the old coupon-growth strategy as current context.

Don't do this if you're trying to keep the demo fast; it is optional.

---

## While testing, verify

- Old node dims.
- New node appears.
- Both nodes fit on screen.
- No manual pan required.
- Right inspector shows useful metadata.
- Old claim remains inspectable.
- New claim is active.

---

# SCENE 4 — Make the consequential business decision

## User action

Enter exactly:

```text
Summit Sisters wants $6,000 for another campaign. Should we renew them?
```

## Expected latency

Approximately:

```text
1.7–1.9 seconds
```

Measured:

```text
Mean: 1.785 sec
Min: 1.705 sec
Max: 1.827 sec
```

No fallback occurred in any of the three final live runs.

---

# 11. Talk track while the recommendation loads

Say:

> “Before the model generates a recommendation, the application constructs the evidence set.”

Then:

> “This distinction matters: the LLM isn't being asked to remember what the data was. The application retrieves and calculates the evidence, then gives the model a bounded reasoning problem.”

---

# 12. Decision Evidence panel

When the card appears, slow down here.

This is one of the strongest moments in the demo.

The visual reading order should be:

```text
Observed performance
        ↓
Relevant governed memory
        ↓
Measurement caution
        ↓
Synthetic AP portfolio experience
        ↓
Recommendation
```

---

## A. Commercial ask

Point out:

```text
Proposed fee: $6,000
Previous fee: $4,200
Increase: +42.9%
```

Say:

> “The commercial ask is 43% above the prior campaign fee.”

Then:

> “That percentage is calculated by application code, not by the model.”

---

## B. Prior performance

Point to:

```text
Sep 2025
$4,000 → $9,840
2.46x attributed ROAS

Feb 2026
$4,000 → $10,120
2.53x

May 2026
$4,200 → $31,240
7.44x
```

Say:

> “The first two campaigns are remarkably consistent at about 2.5x attributed ROAS, then May jumps to 7.4x.”

Do not call attributed revenue incremental revenue.

---

## C. Relevant governed memory

Point out:

```text
Reduce coupon dependence
Prioritize new-customer acquisition
Accept somewhat lower short-term ROAS
```

Say:

> “This is where the conversation we just had actually changes the recommendation context.”

Then:

> “The old coupon-growth strategy is still historically available, but it is absent here because it's no longer active.”

That is an excellent proof of the memory lifecycle.

---

## D. Measurement caution

Point to:

```text
1,847 code redemptions
385 tracked clicks

Unverified hypothesis
```

Say:

> “I'm deliberately not calling this confirmed promo-code leakage. The system stores it as an attribution-integrity hypothesis.”

Then:

> “A model inference and a verified client statement should never carry equal authority.”

This is one of your strongest lines.

---

## E. Portfolio experience

Point to:

```text
SYNTHETIC
31 comparable cases
21 positive outcomes
```

Say clearly:

> “For the case study, this portfolio layer is synthetic. I'm using it to demonstrate what privacy-safe AP institutional experience could look like, not representing these as real AP client results.”

Then:

> “The intent isn't that one historical pattern becomes universal truth. It's supporting evidence.”

---

# 13. Recommendation result

The final verified recommendation was consistently:

```text
renew_with_hybrid_compensation
```

Across the three final runs:

```text
Base fee: $4,200
Performance bonus: 15%
Basis: verified_new_customer_revenue
```

Confidence varied naturally:

```text
0.70–0.75
```



---

## Talk track

Say:

> “The recommendation is to renew, but not simply accept the $6,000 flat fee. The agent recommends maintaining a lower guaranteed base and tying more of the upside to verified new-customer performance.”

Then:

> “That's aligned with the client's current objective, recognizes that Summit Sisters has promising prior commerce performance, but doesn't blindly capitalize the anomalous May attribution result.”

---

# 14. Important architecture explanation

If you want to pause here technically:

> “Every hard number in this panel is generated deterministically from the database before the LLM is called.”

Then explain:

```text
Database
   ↓
Recommendation retrieval
   ↓
DecisionEvidence
   ↓
LLM receives compact evidence brief
   ↓
Recommendation prose / reasoning
```

Supporting memory IDs are also created server-side from the actual retrieved rows.

Say:

> “I don't ask the model to tell me which records it used and then trust whatever IDs it generates. The retrieval layer determines the evidence set, and the application attaches the real record IDs.”

---

## Exact backend input / output contract

**Input sent to the model** — not raw DB rows, a compact plain-text digest (`evidence_brief`) assembled by `build_recommendation_context()`, plus a small structured `context` dict:

```text
TRUSTED CLIENT MEMORY
- Northwind Outfitters partnership strategy: reduce coupon dependence.
- Northwind Outfitters primary growth objective: new customer acquisition.
- Northwind Outfitters accepts tradeoff: lower short term roas.

CURRENT PARTNER DATA
- Summit Sisters has 3 prior campaign(s) with attributed revenue up to $31,240.
- The 2026-05 campaign shows an unusual redemption-to-click relationship (1847 redemptions vs 385 clicks).

PORTFOLIO EXPERIENCE
- 31 comparable creator-renewal decisions across AP's synthetic portfolio (21 positive).
- Hybrid compensation succeeded 71% of the time vs 45% for flat-fee renewal in comparable cases (synthetic AP portfolio data).

CAUTION
- possible promo code leakage is an unverified hypothesis (confidence 0.65), not a confirmed fact.
```

```json
{"client_name": "Northwind Outfitters", "partner_name": "Summit Sisters", "primary_goal": "new customer acquisition", "strategy": "reduce coupon dependence", "has_attribution_hypothesis": true, "has_hybrid_pattern": true, "prior_fee": 4200}
```

The system prompt (`RECOMMENDATION_SYSTEM_PROMPT`) sets hard rules: treat TRUSTED CLIENT MEMORY / CURRENT PARTNER DATA as reliable; treat CAUTION items as unverified hypotheses, call them out explicitly if they bear on the recommendation, never state them as fact; treat PORTFOLIO EXPERIENCE as supporting evidence from comparable cases, not universal truth or proof of causality; never convert attributed revenue into causal incrementality; if a caution casts doubt on how a metric was tracked, prefer a bonus basis the caution doesn't call into question (e.g. `verified_new_customer_revenue` over raw `attributed_revenue`); never invent a metric absent from the brief.

**What the model is asked to produce:**

```json
{
  "recommendation": "renew_with_hybrid_compensation",
  "recommended_terms": { "base_fee": 4200, "performance_bonus_pct": 15, "bonus_basis": "verified_new_customer_revenue" },
  "confidence": 0.74,
  "uncertainties": ["Promo-code leakage is suspected but not verified."],
  "explanation": "..."
}
```

Note what is deliberately **not** in that shape: no `supporting_memory_ids` field exists on the validation schema at all — even if a model included one, `RawRecommendationOut.model_dump()` would silently drop it. The model is never given the opportunity to claim which records it used.

**How the output is generated / governed:**

```text
question + evidence_brief + context
   ↓
call_with_fallback("recommend", question, evidence_brief, context, validate=validate_raw_recommendation)
   ↓
RawRecommendationOut Pydantic validation
     — recommendation non-blank
     — recommended_terms.base_fee > 0
     — recommended_terms.performance_bonus_pct in [0, 100]
     — confidence in [0.0, 1.0]
   ↓                              ↓ invalid / call errors
  valid                    mock provider's own deterministic recommend() runs instead —
   ↓                        the same fallback path as every other bounded call
RecommendationResponse assembled
```

Everything in the Decision Evidence panel itself — `commercial_ask` (proposed fee, prior fee, % increase), `prior_performance` (per-campaign fee/revenue/ROAS), `measurement_cautions`, `client_memory`, `portfolio_evidence` — is a separate object (`DecisionEvidence`) built in the *same* Python function, from the *same* retrieved rows, **before** the model is ever called. The model never sees this structured object and never produces any part of it; it only ever sees the prose `evidence_brief` version of the same facts.

---

# SCENE 5 — Capture the decision

## User action

Click:

**Accept recommendation**

## Expected response

Near-instant:

```text
~12 ms backend endpoint
```

A Decision node should appear.

The graph should automatically focus on it.

Decision wording should correctly resolve:

```text
Renew Summit Sisters under renew with hybrid compensation
```

The final smoke test specifically found and fixed the prior frontend name-resolution defect here.

---

## Talk track

Say:

> “Now the organization is capturing something reporting systems usually miss.”

Then point to the new node:

> “We're not just recording that Summit Sisters was renewed. We're capturing why that decision was made and linking it to the evidence that motivated it.”

Then:

> “That's important because six months from now the next account manager shouldn't have to reconstruct the rationale from Slack messages and old decks.”

---

## What the system actually persists

A real Decision row is created with:

- Northwind;
- Summit Sisters;
- decision;
- recommended terms;
- status;
- rationale;
- supporting evidence relationships.

Graph edges include relationships such as:

```text
Northwind
   ↓
MADE_DECISION
   ↓
Decision

Decision
   ↓
APPLIES_TO
   ↓
Summit Sisters

Decision
   ↓
MOTIVATED_BY
   ↓
Relevant memories
```

---

## No model call in this step

**Input:** exactly the `recommendation`/`recommended_terms`/`explanation`/`supporting_memory_ids` the frontend already holds in memory from Scene 4's response — nothing is re-fetched or re-asked of the model. **Output:** a single `POST /api/decisions` call that inserts one `Decision` row plus the three graph edges above (`motivated_by_claim_ids` fans out into one `MOTIVATED_BY` edge per id). No LLM call happens on Accept — the decision text you're capturing here was already generated a step earlier; this click only makes it durable.

---

## While testing, verify

- Decision node is visible.
- Name says **Summit Sisters**, properly capitalized.
- Viewport focuses smoothly.
- Activity feed updates.
- Right inspector can inspect the Decision.
- No manual reload required.

---

# SCENE 6 — Close the learning loop

## User action

Click:

**Simulate future outcome**

The UI explicitly labels this as demo-only.

## Expected response

Near-instant:

```text
~9 ms
```

The system creates an Outcome node.

The portfolio pattern updates:

```text
Evidence count:
31 → 32

Positive outcomes:
21 → 22
```

---

## No model call in this step

Also fully deterministic, and explicitly demo-only: `POST /api/decisions/{id}/simulate-outcome` seeds `random.Random(decision_id)` — keyed off the decision's own id, so re-running it against the same decision always produces the same numbers — then computes:

```text
verified_new_customer_revenue = round(base_fee * uniform(5.5, 6.5), -2)
attributed_revenue            = round(verified_new_customer_revenue * uniform(1.3, 1.5), -2)
```

off the decision's own `base_fee`, always labeled `outcome_label: "positive"` and `is_simulated: true`. **Input:** the decision's stored terms. **Output:** one `Outcome` row, a `RESULTED_IN` edge, and — only if the decision's `motivated_by_claim_ids` included the hybrid portfolio pattern's id — a call to `execute_promote_pattern_evidence()`, which increments that pattern's `evidence_count`/`positive_outcomes` by exactly 1 and appends the decision id to `supporting_decision_ids`. No model call, and nothing here claims to represent a real commercial result — a production version would replace this endpoint with an ingestion pipeline reading actual downstream campaign performance, not a random-number generator.

---

# 15. Talk track for the finale

Before clicking:

> “Obviously, during a live case study I can't wait months for the actual commercial outcome, so this next control is explicitly simulated.”

Click.

As the Outcome appears:

> “Production would ingest the real downstream outcome. Structurally, though, this is the same learning loop.”

Then point to the portfolio count:

> “The decision and result have now become another episode in AP's evidence base.”

Then deliver the core close:

> “And importantly, that's not just a visual counter.”

If you want to prove it:

> “A future recommendation now reads 32 cases from the database instead of 31.”

Then finish:

> **“Every client engagement makes AP smarter.”**

Pause.

That should be the end of the live demo.

---

# 16. What just happened — technical recap

After the live demo, summarize:

```text
Conversation
     ↓
LLM extraction
     ↓
Pydantic validation
     ↓
Deterministic normalization
     ↓
Human review
     ↓
Versioned memory
     ↓
Deterministic retrieval
     ↓
DecisionEvidence
     +
LLM reasoning
     ↓
Decision
     ↓
Outcome
     ↓
Updated portfolio evidence
```

Then say:

> “This is a bounded agentic system. I intentionally didn't build an open-ended autonomous loop.”

---

## Which of the six scenes actually call the model

Worth having ready if asked directly — only half the scenes touch the LLM at all:

```text
Scene 1  Bring me up to speed        LLM call   (summarize — plain prose, no JSON/validation)
Scene 2  Teach the system something  LLM call   (extract_claims — JSON, Pydantic-validated)
Scene 3  Approve → Supersede         no model   (deterministic state transition on Scene 2's already-generated content)
Scene 4  Renewal decision            LLM call   (recommend — JSON, Pydantic-validated)
Scene 5  Accept recommendation       no model   (persists exactly what Scene 4 already produced)
Scene 6  Simulate future outcome     no model   (seeded RNG, explicitly demo-only)
```

Every LLM call above shares the same contract: the application builds the evidence *before* the call, validates the model's output *after* the call (`RawXOut` Pydantic schema, or nothing to validate for Scene 1's plain-text case), and falls back to a deterministic mock implementation of that same method on any call failure or validation failure — never an unhandled exception, never unvalidated data reaching a router.

---

# 17. If asked what agent framework you used

Say:

> “I used a lightweight custom agent architecture rather than LangGraph or another orchestration framework. I only needed a handful of bounded model responsibilities—memory extraction, summarization and recommendation reasoning. Everything stateful or high-impact is handled by deterministic application services.”

Then:

> “For this workflow, introducing a graph orchestration framework would have added abstraction without solving an actual orchestration problem.”

---

# 18. LLM responsibilities vs application responsibilities

## LLM

The model handles:

- candidate memory extraction;
- natural-language summarization;
- recommendation reasoning;
- recommendation explanation.

## Application logic

Deterministic code handles:

- Pydantic schema validation;
- canonical predicates;
- predicate alias normalization;
- IDs;
- timestamps;
- source authority;
- client scope;
- conflict lookup;
- active/superseded state transitions;
- validity windows;
- retrieval filters;
- campaign calculations;
- ROAS;
- fee increase percentage;
- supporting evidence IDs;
- persistence;
- portfolio evidence counts;
- graph construction.

Use this line:

> **“The model proposes and reasons; application logic governs and persists.”**

---

# 19. Why this isn't just RAG

Expect this question.

Answer:

> “RAG solves retrieval. This problem also requires knowledge lifecycle and governance.”

Then explain:

> “A client strategy can become stale. Two people can disagree. A model inference may be uncertain. One outcome shouldn't become organizational truth. A new statement can supersede an old one without deleting history.”

Then:

> “Semantic retrieval would absolutely become part of the production retrieval layer, but embeddings alone don't solve those memory-governance problems.”

---

# 20. What's real in the prototype

Be explicit.

## Real

- live OpenAI extraction;
- Pydantic extraction validation;
- predicate normalization;
- candidate-memory persistence;
- human approval;
- deterministic conflict detection;
- SUPERSEDE;
- validity windows;
- old-memory retention;
- active-memory filtering;
- SQLite persistence;
- graph generation;
- recommendation retrieval;
- deterministic DecisionEvidence;
- live recommendation call;
- server-generated supporting memory IDs;
- Decision persistence;
- Outcome persistence;
- portfolio evidence-count update;
- reset/recovery logic.

The final verification successfully completed all six scenes in three consecutive live-model runs with zero fallbacks.

---

# 21. What's simplified or synthetic

Say this directly.

## Synthetic portfolio evidence

The:

```text
31 comparable decisions
21 positive outcomes
```

are fictional demonstration data.

## Simulated outcome

The future Northwind outcome is generated for demo purposes.

The resulting DB row and graph update are real application behavior, but the economic outcome is simulated.

## SQLite

Real persistence, but intentionally prototype-scale.

## Cross-client privacy

Represented through scopes and filtering, but not production-grade tenant isolation.

## Authentication/RBAC

Not implemented.

## Semantic retrieval

Not implemented.

## AWS / AgentCore deployment

Not implemented in this prototype.

---

# 22. Production architecture narrative

Say:

> “I deliberately optimized the prototype for five to six focused hours of reliable product behavior rather than production infrastructure.”

Then:

> “If this became an AP product, I would preserve the same conceptual boundaries but replace the local infrastructure.”

Use:

```text
Existing AP application
        ↓
Application/API layer
        ↓
Memory + Decision services
        ↓
AgentCore Runtime
        ↓
Amazon Bedrock
        │
        ├── Aurora PostgreSQL
        │       ↓
        │    pgvector
        │
        └── S3 immutable evidence

IAM / KMS / CloudWatch
```

Do not claim every component is mandatory.

---

# 23. Why Aurora PostgreSQL before Neptune

If asked:

> “Why not immediately use a graph database?”

Answer:

> “Because the existence of a graph visualization doesn't automatically imply a graph database is the best canonical store.”

Then:

> “Most of the current workload is still relational—claims, statuses, validity windows, scopes, decisions and outcomes. I'd start with managed PostgreSQL and explicit edge tables.”

Then:

> “If production queries evolve toward complex multi-hop traversals where relational queries become operationally painful, Neptune becomes much easier to justify.”

---

# 24. What breaks first at 200+ clients

Present these in this order.

## 1. Cross-client privacy

Current prototype:

```text
application-level client_id filtering
```

Risk:

A future endpoint could accidentally omit the filter.

Production:

- hard tenant boundaries;
- PostgreSQL row-level security or equivalent;
- IAM;
- RBAC;
- privacy-safe aggregation;
- audit logging.

Say:

> “The most dangerous scaling failure isn't a slow query. It's accidentally surfacing one client's proprietary information to another.”

---

## 2. Memory pollution and stale knowledge

As memory grows:

- low-value claims accumulate;
- old strategy becomes stale;
- contradictory inputs increase.

Production:

- stricter memory-write thresholds;
- review queues;
- expiration;
- consolidation;
- promotion/demotion;
- source authority;
- retention policies.

---

## 3. Retrieval volume

Current prototype scores a relatively small set of memories in application code.

At scale:

- DB indexes;
- candidate retrieval in SQL;
- pgvector/OpenSearch;
- reranking;
- context budgets.

---

## 4. Ontology / entity resolution

Current deterministic alias table works for the demo.

At scale:

- creator aliases;
- network names;
- publisher variants;
- changing client terminology.

Production:

- canonical entity service;
- aliases;
- governed ontology;
- human resolution for ambiguous cases.

---

## 5. Concurrent LLM traffic

Current prototype can fall back safely if a model call errors.

At production concurrency:

- rate limits;
- backpressure;
- retries;
- queues;
- observability;
- cost controls;
- model-routing policies.

---

# 25. Rollout strategy

The brief explicitly asks how you would get hundreds of non-technical account managers using the product.

Do not answer:

> “Launch the enterprise knowledge graph.”

Instead:

> “I would launch one narrow workflow: creator renewal decision support.”

---

## Phase 1 — Shadow mode

Pilot:

```text
5–10 account teams
```

System:

- extracts candidate memory;
- recommends decisions;
- cannot silently alter important memory;
- logs agreement/disagreement.

Goal:

- validate trust;
- understand false memories;
- find missing context;
- evaluate recommendation usefulness.

---

## Phase 2 — Assisted mode

Enable:

- one-click memory approval;
- conflict resolution;
- account briefs;
- decision capture.

Account managers need to learn three things:

1. Tell the system meaningful context naturally.
2. Review what it proposes to remember.
3. Correct stale beliefs.

---

## Phase 3 — Expanded institutional intelligence

Then add:

- publisher negotiations;
- placement history;
- partner recruitment;
- account handoffs;
- commercial terms;
- broader portfolio patterns.

---

# 26. Adoption story

Say:

> “I wouldn't train account managers on embeddings, graphs or agent frameworks.”

Instead:

> “I'd frame it around a job they already do.”

Example:

> “When you're deciding whether to renew a creator, the relevant account history and AP experience should already be there.”

Then measure whether that workflow becomes easier.

---

# 27. Business measurement

The case brief explicitly says success should be measured in business terms rather than usage statistics.

## Account continuity

Measure:

- time for a new account manager to become independently effective;
- time spent reconstructing historical decisions;
- client questions requiring manual historical research.

---

## Decision quality

Measure:

- repeated tactics that AP had previously learned were ineffective;
- recommendation override rate;
- commercial outcomes of supported renewals;
- stale knowledge that would otherwise have affected a decision.

---

## Revenue protected / created

Examples:

- poor renewals avoided;
- terms improved through remembered historical context;
- successful partnership patterns reused;
- commercial leakage avoided.

---

## Long-term client outcomes

Eventually:

- retention;
- expansion;
- executive satisfaction;
- account-team continuity.

---

## Operational metrics

Use diagnostically, not as the primary value claim:

- candidate-memory acceptance;
- candidate rejection;
- conflict frequency;
- retrieval precision;
- latency;
- model fallback rate;
- cost per decision;
- recommendation override rate.

---

# 28. Reliability story

Your final validation showed:

```text
Backend tests:
44 passed

Frontend TypeScript:
PASS

Lint:
0 errors
0 warnings

Production build:
PASS
```

The three final live-model runs all produced:

```text
3 expected strategy candidates
correct SUPERSEDE conflict
renew_with_hybrid_compensation
no fallback
```

Only confidence/prose varied slightly, as expected.

---

# 29. LLM failure behavior

If asked:

> “What happens if the LLM fails?”

Answer:

> “External model output is treated as untrusted.”

Extraction:

```text
LLM
 ↓
Pydantic validation
 ↓
invalid extraction rejected
```

Recommendation:

```text
LLM
 ↓
RawRecommendationOut
 ↓
invalid
 ↓
deterministic fallback
```

Also:

> “Supporting evidence IDs are never supplied by the model. They're constructed from the actual records retrieved by application code.”

---

# 30. Important nuance about semantic errors

Do not overclaim Pydantic.

Say:

> “Schema validation catches malformed or structurally invalid model output. It doesn't prove that every semantically valid extraction is correct.”

That is why the application also has:

- constrained predicates;
- source authority;
- conflict detection;
- candidate review;
- human approval.

---

# 31. Emergency recovery during the live demo

## Dirty demo state

Click:

**Reset demo → Yes, reset**

Approximately:

```text
39 ms
```

No server restart required.

---

## OpenAI failure

The app automatically uses deterministic fallback behavior when the provider call fails or returns structurally invalid output.

Continue the demo.

If necessary, say:

> “The model provider failed, so the application used its fallback path. That separation is intentional.”

Do not panic and restart everything unless necessary.

---

## Backend down

Terminal:

```bash
cd /Users/nicklynch/Documents/Projects/ap_intelligence/ap-intelligence-graph/backend
uv run uvicorn app.main:app --port 8000
```

Wait for Uvicorn.

Then retry.

---

## Frontend down

Terminal:

```bash
cd /Users/nicklynch/Documents/Projects/ap_intelligence/ap-intelligence-graph/frontend
npm run dev
```

Reload:

```text
http://localhost:3000
```

Backend state is preserved.

---

# 32. Manual rehearsal checklist

Before declaring yourself finished, run the whole flow and answer:

- [ ] Can I read every important node at my screen-sharing resolution?
- [ ] Does the right panel default to Northwind?
- [ ] Is SYNTHETIC obvious on the portfolio pattern?
- [ ] Does candidate review fit comfortably?
- [ ] Does SUPERSEDE visually communicate old vs new?
- [ ] Is graph auto-focus smooth rather than disorienting?
- [ ] Does the Decision Evidence panel feel readable rather than crowded?
- [ ] Is the measurement caution visibly distinct?
- [ ] Does Summit Sisters render correctly in the Decision?
- [ ] Does the outcome/pattern transition clearly show 31 → 32?
- [ ] Do I know exactly where I need to click next?
- [ ] Can I narrate naturally through the ~2-second waits?
- [ ] Can I complete all six scenes without consulting notes?

---

# 33. Condensed six-scene presenter card

If you want a small cheat sheet beside your laptop, use this.

## Scene 1

**Do**

```text
Bring me up to speed on Northwind.
```

**Say**

> “The agent is retrieving only what AP currently believes to be true.”

---

## Scene 2

**Do**

Paste strategy update.

**Say while loading**

> “This is where I use the model: translating normal account-team conversation into candidate structured knowledge.”

**When card appears**

> “Nothing has been written yet. These are proposals.”

---

## Scene 3

**Do**

Approve → Supersede.

**Say**

> “The system can change its mind without forgetting its history.”

---

## Scene 4

**Do**

```text
Summit Sisters wants $6,000 for another campaign. Should we renew them?
```

**Say while loading**

> “The application is assembling the evidence before the model reasons.”

**Then**

> “Every hard number here comes from application code and database records.”

---

## Scene 5

**Do**

Accept recommendation.

**Say**

> “Now we're preserving not just what we decided, but why.”

---

## Scene 6

**Do**

Simulate future outcome.

**Say**

> “The result becomes another episode in AP's institutional evidence.”

Then:

> “And a future recommendation now reads 32 cases instead of 31.”

Finish:

> **“Every client engagement makes AP smarter.”**

---

# 34. Key lines worth memorizing

> **The model proposes; application logic governs and persists.**

> **The system can change its mind without forgetting its history.**

> **A model inference and a verified client statement should never have equal authority.**

> **One successful campaign is an episode; repeated evidence can become institutional knowledge.**

> **The graph isn't the product. The product is making prior organizational learning available at the moment of the next decision.**

> **The LLM reasons over evidence; it does not own the evidence.**

> **Every client engagement makes AP smarter.**

---

# 35. Final testing protocol

For each rehearsal:

### Before

```text
1. Health check
2. Reset demo
3. Confirm OpenAI provider
4. Confirm opening graph
5. Confirm Northwind inspector
```

### Run

```text
Scene 1
Scene 2
Scene 3
Scene 4
Scene 5
Scene 6
```

### After

Confirm:

```text
Decision exists
Outcome exists
Portfolio pattern = 32
```

Then:

**Reset demo**

Confirm:

```text
Portfolio pattern = 31
Old strategy active
Decision/outcome removed
```

Once you can run this flow comfortably three times in a row, stop changing the code.

The engineering work is complete. The remaining work is presenter fluency.