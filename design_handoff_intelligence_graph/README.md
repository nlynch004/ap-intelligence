# Handoff: AP Intelligence — Visual Enhancement

## Overview

This package documents a visual redesign of the **AP Intelligence** prototype
(`ap-intelligence-graph/frontend`, Next.js + React Flow + Tailwind). The work is a
**presentation-layer change only**: no backend, memory lifecycle, retrieval, conflict
resolution, recommendation, decision, outcome, reset, or seed behavior changes.

Goals delivered:

1. Dark, enterprise-grade theme (deep blue-grey surfaces, restrained semantic color).
2. Graph nodes and edges that are readable and traceable (bigger type, hover/select tracing,
   progressive edge labels).
3. Chat panel reframed as a guided workflow with a grouped Decision Evidence card.
4. Right panel reframed as a contextual object inspector + event timeline.
5. Workspace ergonomics: draggable nodes, resizable panels, hideable panels, zoom / fit /
   reset-layout controls.

## About the Design Files

The files in this bundle are **design references authored in HTML** (Design Component format —
a single `.dc.html` per design, streamed by `support.js`). They are prototypes that show
intended look and behavior. **Do not ship them.** The task is to recreate them inside the
existing `frontend/` Next.js app using its established patterns: React function components,
Tailwind utilities, CSS custom properties in `app/globals.css`, `@xyflow/react` for the graph,
and the existing `lib/types.ts` data contracts.

Mock data in the prototypes stands in for real API state. In production every value must come
from the existing sources (`api.getGraph`, `api.getActivity`, `api.sendChat`,
`DecisionEvidence`, `RecommendationResponse`, candidate/conflict/decision/outcome state).

- `AP Intelligence Graph v2.dc.html` — **the target design. Implement this one.**
- `AP Intelligence Graph v1.dc.html` — earlier, higher-contrast neon iteration. Reference only.
- `support.js` — runtime needed to open the `.dc.html` files locally in a browser.

## Fidelity

**High fidelity.** Colors, type sizes, spacing, and interaction states below are final and
exact. Recreate pixel-for-pixel using Tailwind/CSS in the target app. Where a value is not
listed, follow the spacing scale in "Design Tokens".

---

## Screens / Views

There is one screen: the single-page workspace (`app/page.tsx`), three regions plus a header.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ● AP Intelligence │ Creator renewal / Summit Sisters   Northwind ◧◨ Reset │
├───────────────┬──────────────────────────────────────────┬───────────────┤
│ Workflow +    │            GRAPH WORKSPACE (hero)        │  Context      │
│ Conversation  │                                          │  + Activity   │
└───────────────┴──────────────────────────────────────────┴───────────────┘
```

### Shell / layout

- Root: `height: 100vh`, `display: flex; flex-direction: column`, `overflow: hidden`,
  background `#090c12`, color `#e6ecf5`, font `'Plus Jakarta Sans'`, base `15px/1.5`.
- Body row: `flex: 1; display: flex; min-height: 0`.
- Left panel: width from state (`chatW`), `flex: 0 1 auto`, `min-width: 240px`, bg `#0b0f16`.
- Center: `flex: 1`, `min-width: 420px`, `position: relative`, bg `#090c12`.
- Right panel: width from state (`inspectorW`), `flex: 0 1 auto`, `min-width: 220px`, bg `#0b0f16`.
- Separators: 1px `#151b26` vertical dividers, which are also the resize handles
  (`cursor: col-resize`).
- Initial widths on mount: `chatW = min(380, innerWidth * 0.28)`,
  `inspectorW = min(330, innerWidth * 0.23)`; clamp floors 240 / 220. Never hardcode px only —
  the center must remain the widest region at laptop widths.
- **No boxed containers.** Hierarchy comes from surface depth (`#090c12` → `#0b0f16` → `#0d1219`
  → `#111823`), whitespace, and text contrast, not borders. Borders are reserved for the
  selected graph node, panel separators, and one section rule inside Decision Evidence.

### 1. Header (56px tall)

- `padding: 0 24px`, bg `#0b0f16`, bottom border `1px solid #151b26`, flex space-between.
- Left cluster, `gap: 12px`, vertically centered:
  - status square: `8×8px`, `border-radius: 2px`, `#4fb98d`.
  - product name: `15px / 600 / #e6ecf5` — "AP Intelligence".
  - divider: `1px × 16px`, `#1c2431`.
  - context: `14px / #94a3ba` — "Creator renewal `/` Summit Sisters"; the slash is `#4b586e`.
- Right cluster, `gap: 16px`:
  - client name: `14px / #c3cfe0` — "Northwind Outfitters".
  - two panel toggles: `26×26px` transparent buttons, glyphs `◧` and `◨`, `13px`.
    Color `#94a3ba` when the panel is visible, `#4f5d75` when hidden.
  - "Reset": `13px / #94a3ba`, transparent, no border.
- The long product tagline from the current build is **removed** from persistent chrome.

### 2. Left panel — Workflow + Conversation

Top block (`padding: 22px 22px 16px`):

- Section label: `11px`, `letter-spacing: 0.09em`, `#5c6a82`, `margin-bottom: 14px` —
  "CREATOR RENEWAL".
- Three workflow steps, `gap: 2px`, each a full-width button:
  - `padding: 11px 12px`, `border-radius: 8px`, no border, `display: flex; gap: 14px`.
  - background `#111823` when the step is current, otherwise transparent.
  - step number: `12px` IBM Plex Mono, `#4f5d75`, `padding-top: 2px`.
  - title: `14px / 600`; color `#e6ecf5` current, `#c3cfe0` complete, `#8c98ad` upcoming.
  - description: `13px / #7b8aa3`, `margin-top: 1px`.
  - status, right-aligned `12px`, `white-space: nowrap`:
    `✓ Complete` `#4fb98d` · `● Current` `#5b9fd4` · `○ Next` `#4f5d75`.
  - Steps: `01 Account context / Retrieve current Northwind context`,
    `02 Strategy update / Capture what changed`,
    `03 Renewal decision / Evaluate Summit Sisters`.
  - Clicking a step at or below the current stage runs the corresponding demo prompt
    (mapping in "State Management").

Conversation block:

- Divider: `border-top: 1px solid #141a25`; heading "CONVERSATION" same style as above.
- Scroll area: `flex: 1; overflow-y: auto; padding: 6px 22px 22px; gap: 14px`.
- User message: right-aligned, bg `#18222f`, `padding: 10px 14px`, `border-radius: 12px`,
  `max-width: 88%`, `14px/1.55`, `#e6ecf5`.
- Assistant message: left-aligned, **no bubble** — transparent, no padding, full width,
  `14px/1.55`, `#b3c0d3`.
- Both enter with `fadeup 0.25s ease`.

### 3. Decision Evidence card (left panel, appears at stage ≥ 3)

Single grouped surface: bg `#0d1219`, `border-radius: 12px`, `padding: 18px`,
enter `fadeup 0.3s ease`. Label "DECISION EVIDENCE" in the `11px/0.09em/#5c6a82` style.
Sub-blocks separated by `margin-bottom: 18px` (no internal cards or borders):

1. **Commercial ask** — label `13px #7b8aa3`; value `16px/600 #e6ecf5` ("$6,000 proposed");
   sub `13px #7b8aa3` ("$4,200 prior fee") with `· +42.9%` in `#c9975a`.
2. **Historical performance** — three rows, `gap: 7px`, `justify-content: space-between`:
   month `14px #c3cfe0`, `fee → revenue` `#94a3ba`, multiple `13px` IBM Plex Mono `#4fb98d`.
   Rows: Sept 2025 `$4,000 → $9,840` `2.46x`; Feb 2026 `$4,000 → $10,120` `2.53x`;
   May 2026 `$4,200 → $31,240` `7.44x`.
3. **Governed context** — four label/value stacks, label `#7b8aa3`, value `#e6ecf5`, `14px`:
   Relationship / Strategy / Primary objective / Negotiation history.
4. **Measurement caution** — the only tinted sub-surface: bg `rgba(201,151,90,0.06)`,
   `border-radius: 10px`, `padding: 14px`. Header row: `△` + "Measurement caution",
   `13px/600 #c9975a`. Title `14px/600 #d5cbb8` ("Attribution integrity anomaly").
   Body `14px/1.55 #a89b85`. Footer `12px` IBM Plex Mono `#8a7e6b` —
   `unverified hypothesis · confidence 0.61`. No warning-red, no icon fill, no bright yellow.
5. **Portfolio experience** — `14px #e6ecf5` with the case count in `#8f83c9`;
   `SYNTHETIC` badge as plain `11px`, `letter-spacing: 0.08em`, `#6b6288` text (no pill).
6. **Recommendation** — separated by `border-top: 1px solid #161d28; padding-top: 16px`.
   Label "RECOMMENDATION"; headline `18px/600 #e6ecf5` ("Renew and test");
   terms `14px #94a3ba`. Primary action button: bg `#4fb98d`, text `#0d1a17`,
   `13px/600`, `padding: 9px 16px`, `border-radius: 8px` — "Simulate outcome"
   (hidden once an outcome exists).

### 4. Center — Graph workspace (the hero)

- Background grid: two 1px `rgba(255,255,255,0.016)` linear gradients at `72px` intervals,
  `pointer-events: none`. No dot grid, no vignette-heavy treatment.
- Scroll/pan container: absolutely positioned, `overflow: auto`, `padding: 72px`.
- Zoom: wrapper sized `worldW * zoom × worldH * zoom`; inner world at natural size with
  `transform: scale(zoom); transform-origin: top left`. World size `2290 × 615`.
- Nodes are absolutely positioned `250px`-wide cards; edges are one `<svg>` behind them.

**Node card**

- `width: 250px`, `padding: 14px 16px`, `border-radius: 10px`,
  `transition: opacity .3s, box-shadow .3s, background .3s`, `cursor: grab`, `user-select: none`.
- Resting: bg `#0c1017`, border `1px solid #151b25`, no shadow.
- Focused (hovered or selected): bg = that node's semantic surface, border = semantic border,
  `box-shadow: 0 0 0 1px <border>, 0 0 0 4px <glow>`. Soft halo only — no neon glow.
- Historical node: bg `#0a0e14`, resting opacity `0.7`, muted text.
- Content order (top to bottom):
  1. type label — `12px`, semantic text color, `margin-bottom: 7px` (e.g. "Strategy", "Decision").
  2. title — `15.5px / 600 / 1.35 / #e6ecf5` (business meaning, e.g. "Reduce coupon dependence").
  3. detail — `13px / #7b8aa3 / 1.45`, `margin-top: 4px` (e.g. "$3,500 base + 10% bonus").
  4. status row — `margin-top: 10px`, `gap: 8px`, `12px` semantic color; plus `SYNTHETIC`
     as `10px / 0.08em / #6b6288` where applicable.
- Statuses are business-readable: `● Active`, `● Active relationship`, `△ Review required`,
  `✓ Accepted`, `✓ Simulated result`, `○ Not yet observed`, `Historical`. The raw system
  status (`superseded`, `needs_review`) appears only in the inspector's SYSTEM group.

**Node inventory** (type · title · detail · status · semantic color · x,y)

| id | type | title | detail | status | color | x | y |
|---|---|---|---|---|---|---|---|
| team_member | Account lead | Jessica Moreno | Northwind · 3 years | — | gray | 0 | 175 |
| client | Client | Northwind Outfitters | eCommerce · 1 open campaign | ● Active relationship | blue | 330 | 175 |
| creator | Creator | Northwind Creator Network | Instagram · TikTok | — | gray | 660 | 30 |
| publisher | Publisher | Summit Sisters | Coupon and content | — | gray | 660 | 310 |
| campaign | Campaign | Summit Sisters — May 2026 | $4,200 fee · 7.44x ROAS | — | gray | 990 | 175 |
| mem_hypothesis | Attribution hypothesis | Promo-code leakage suspected | 1,847 redemptions · 385 clicks | △ Review required | amber | 1320 | 0 |
| mem_active | Strategy | Reduce coupon dependence | Grow new customers | ● Active | blue | 1320 | 185 |
| mem_superseded | Strategy | Grow coupon partnerships | — | Historical | hist | 1320 | 370 |
| decision | Decision | Renew and test | $3,500 base + 10% bonus | ✓ Accepted | green | 1650 | 185 |
| outcome | Outcome | +$412 attributed revenue | — | ✓ Simulated result / ○ Not yet observed | green | 1980 | 185 |
| portfolio_pattern | Portfolio pattern | Coupon-dependent creators underperform | `31` or `31 → 32` comparable cases + SYNTHETIC | — | purple | 1980 | 385 |

In production, positions come from the existing columnar layout in `IntelligenceGraph.tsx`
(one column per `node_type`); increase its column pitch to ~330px and row pitch to ~185px to
match this spacing, and keep node drag overrides in local component state.

**Edges**

- Cubic bezier from source right-middle to target left-middle; anchor offset `y + 52`;
  control-point offset `max(70, (tx - sx) * 0.5)`.
- Resting: `stroke-width: 1.2`, `opacity: 0.5`. Touching the focused node: `1.8`, `opacity: 1`.
  Unrelated while something is focused: `opacity: 0.12`.
- Dashed `4 4` for supersedes / risk / motivated-by. Arrowheads: 6×6 marker per semantic color.
- **Labels are progressive**: rendered only when an endpoint is hovered/selected, or when the
  relationship is inherently meaningful (`supersedes`, `resulted in` — always shown).
  Label type `11.5px` Plus Jakarta Sans, semantic text color, centered, `y - 7` above the path.
  No label background boxes.
- `resulted in` animates `edgeflow 0.7s linear infinite` (dash `5 5`) once an outcome exists.

| edge | relationship label | color | dashed | always labeled |
|---|---|---|---|---|
| team_member → client | manages | gray | no | no |
| client → campaign | has campaign | gray | no | no |
| client → creator | has relationship | gray | no | no |
| creator → publisher | worked with | gray | no | no |
| publisher → campaign | applies to | gray | no | no |
| client → mem_active | current strategy | blue | no | no |
| mem_active → mem_superseded | supersedes | hist | yes | **yes** |
| campaign → mem_hypothesis | raises risk | amber | yes | no |
| decision → mem_active | motivated by | blue | yes | no |
| decision → mem_hypothesis | motivated by | amber | yes | no |
| portfolio_pattern → decision | supports | purple | no | no |
| team_member → decision | made decision | green | no | no |
| decision → outcome | resulted in | green | no | **yes** |

**Controls** (bottom-right, `20px` inset, deliberately quiet)

- Row: `gap: 14px`. "Legend" / "Hide legend" text button `12px #5c6a82`.
- Icon group `gap: 2px`, four `26×26px` transparent buttons, color `#5c6a82`:
  `−` zoom out (step 0.12, floor 0.4) · `+` zoom in (ceiling 1.5) ·
  `⛶` fit to view (compute `min((w-60)/worldW, (h-60)/worldH, 1)`, floor 0.4, scroll to 0,0) ·
  `↺` reset layout (zoom 1, clear node drag overrides, scroll to 0,0).
- Legend popover (when open): bg `#0d1219`, `border-radius: 10px`, `padding: 16px 18px`,
  `box-shadow: 0 8px 24px rgba(0,0,0,0.5)`, `13px #94a3ba`, five `7×7px` swatch rows:
  blue "Client context & memory", amber "Uncertainty & review", green "Decision & outcome",
  purple "Portfolio intelligence", `#3d4859` "Historical"; footer hint
  `12px #5c6a82` — "Select a node to reveal its relationships".

### 5. Right panel — Context inspector + Activity

Inspector (`flex: 1.15`, `padding: 22px`, scrolls):

- "CONTEXT" section label.
- Object title `19px / 600 / 1.3 / #e6ecf5`; object type `13px / #7b8aa3`, `margin-top: 3px`.
- Status line `13px`, semantic color, `margin-top: 12px`.
- Grouped sections, `margin-top: 26px`, group label in the `11px/0.09em/#5c6a82` style,
  rows `gap: 14px`: row label `13px #7b8aa3`, row value `14.5px #dbe4f0`.
  Values that are system metadata render in IBM Plex Mono.
- Optional closing note `13.5px / 1.6 / #8c98ad`.
- Groups per object (implement from real API fields):
  - **Client** — OVERVIEW (Industry, Open campaigns) · CURRENT STRATEGY (Strategy,
    Primary objective, Accepted tradeoff) · RELATED (Summit Sisters — Publisher,
    Jessica Moreno — Account lead).
  - **Memory claim (active)** — SOURCE (Origin, Context) · VALIDITY (Effective) ·
    HISTORY (Supersedes) · SYSTEM (claim class, confidence, authority — mono).
  - **Memory claim (historical)** — VALIDITY · HISTORY (Superseded by) · SYSTEM, plus note:
    "Excluded from retrieval but preserved for audit…".
  - **Hypothesis** — SOURCE · SYSTEM (claim class, status, confidence), plus review note.
  - **Campaign** — COMMERCIALS (Flat fee, Attributed revenue, ROAS) · MEASUREMENT
    (Link clicks, Code redemptions — mono).
  - **Decision** — TERMS (Base fee, Performance bonus, Bonus basis) · MOTIVATED BY.
  - **Outcome** — RESULT · SYSTEM (Simulated), plus demo-outcome note.
  - **Portfolio pattern** — EVIDENCE (Comparable cases, Positive outcomes, Hybrid success rate)
    · SCOPE (Visibility: Privacy-safe AP portfolio), plus synthetic note.

Activity timeline (`flex: 1`, `padding: 22px`, `border-top: 1px solid #141a25`, scrolls):

- "ACTIVITY" label, `margin-bottom: 18px`.
- Each event: `display: flex; gap: 14px`. Rail column: `6px` dot (`border-radius: 50%`,
  semantic color) then a `1px` `#1a2130` connector line (`min-height: 26px`, flexes).
- Content: title `14px / 600 / #dbe4f0`; description `13px / #8c98ad / 1.5`;
  timestamp last, `12px` IBM Plex Mono `#5c6a82`, `margin-top: 5px`.
  Raw event types (`SEED`, `CREATE`, `SUPERSEDE`) are **not** displayed — the human title
  carries the meaning. Map: extraction → "Candidate memories extracted",
  supersede → "Strategy updated", decision → "Decision captured",
  outcome → "Outcome recorded".
- New entries animate in with `fadeup 0.4s ease`.

---

## Interactions & Behavior

- **Hover a node** — that node plus its 1-hop neighbors stay at `opacity: 1`; every other node
  drops to `0.3`, unrelated edges to `0.12`; the focused node's edges thicken and reveal labels.
- **Click a node** — becomes the selected node (same focus treatment, persists after mouse-out)
  and drives the inspector. Selection is the app's answer to "what is the inspector explaining".
- **Drag a node** — `mousedown` on a card starts a drag; delta is divided by the current zoom;
  positions live in component state and edges re-route live. `↺` clears the overrides.
- **Resize panels** — `mousedown` on either 1px divider; clamps chat 240–560, inspector 220–520.
- **Hide panels** — `◧` / `◨` in the header unmount the left/right panels so the graph fills
  the width; glyph dims when hidden.
- **Zoom / fit / reset** — as described in Controls.
- **Workflow steps** — clicking step *n* (only when `n <= stage`) posts that scripted prompt and
  advances the stage; production wires these to the real `api.sendChat` calls in the demo script.
- **Simulate outcome** — appends the outcome message, marks the outcome node
  `✓ Simulated result`, animates the portfolio count `31 → 32` (`countpop 0.7s ease`),
  starts the `resulted in` edge dash flow, and appends the timeline entry.
- **Reset** — clears messages, stage, simulated flag, selection (back to client), and node
  drag overrides. In production this rides the existing demo-reset endpoint; workflow state
  must remain a projection of real application state, never a second source of truth.

### Animations

```css
@keyframes edgeflow { to { stroke-dashoffset: -22; } }
@keyframes countpop { 0% { opacity:.35; transform: translateY(2px); } 60% { opacity:1; } 100% { opacity:1; transform: translateY(0); } }
@keyframes fadeup  { from { opacity:0; transform: translateY(4px); } to { opacity:1; transform: translateY(0); } }
```

Transitions: node `opacity .3s`, `box-shadow .3s`, `background .3s`; edge group `opacity .3s`.
No confetti, bounce, or large-scale motion.

---

## State Management

Presentation-only state (all client-side, none persisted):

| state | type | purpose |
|---|---|---|
| `hoveredId` | string \| null | hover tracing |
| `selectedId` | string | inspector subject; defaults to the client node |
| `stage` | 0–3 | workflow progress; derived in prod from candidates/conflict/recommendation state |
| `simulated` | boolean | derived in prod from outcome existence |
| `zoom` | number 0.4–1.5 | graph scale |
| `legendOpen` | boolean | legend popover |
| `chatW` / `inspectorW` | number | panel widths (initialized from viewport) |
| `chatVisible` / `inspectorVisible` | boolean | panel collapse |
| `nodePos` | `Record<id, {x,y}>` | node drag overrides |
| `dragMode` | `'chat' \| 'inspector' \| 'node' \| null` | active pointer gesture |

Derived-state rules for the workflow (do not persist these):

```
brief retrieved                      → step 01 complete
candidates extracted                 → step 02 available/complete
new strategy active + old superseded  → step 02 complete
recommendation exists                → step 03 complete, evidence card visible
decision exists                      → recommendation shows accepted terms
outcome exists                       → simulated = true, portfolio count reflects 32
```

Pointer gestures use `window` `mousemove` / `mouseup` listeners registered on mount and removed
on unmount.

---

## Design Tokens

**Surfaces**

| token | value | use |
|---|---|---|
| app background | `#090c12` | root, graph canvas |
| panel | `#0b0f16` | header, left panel, right panel |
| raised | `#0d1219` | Decision Evidence card, legend popover |
| active row | `#111823` | current workflow step |
| node resting | `#0c1017` | graph node card |
| node historical | `#0a0e14` | superseded node |
| separator | `#151b26` | panel dividers, header rule |
| separator (inner) | `#141a25` / `#161d28` / `#1a2130` | panel section rules, timeline rail |
| node border resting | `#151b25` | graph node card |

**Text contrast tiers**

| tier | value |
|---|---|
| primary business content | `#e6ecf5` |
| strong secondary | `#dbe4f0` / `#c3cfe0` |
| secondary description | `#94a3ba` / `#8c98ad` |
| metadata | `#7b8aa3` |
| faint metadata / labels | `#5c6a82` / `#4f5d75` |
| historical | `#7d889b` title, `#5d6b81` status |

**Semantic families** (`line` = edge/arrow, `node` = focused surface, `border`, `text`, `glow`)

| family | meaning | line | node | border | text | glow |
|---|---|---|---|---|---|---|
| blue | client context & memory | `#4a7fa8` | `#0e1620` | `#1c2b3a` | `#8fbfe3` | `rgba(91,159,212,0.22)` |
| green | decision & outcome | `#3f8f6d` | `#0d1a17` | `#1b3229` | `#6fd0a5` | `rgba(79,185,141,0.22)` |
| amber | uncertainty & review | `#9c7745` | `#191510` | `#33291b` | `#d2a468` | `rgba(201,151,90,0.2)` |
| purple | portfolio intelligence | `#6d61a4` | `#14131f` | `#272338` | `#a599dd` | `rgba(143,131,201,0.2)` |
| gray | structural entities | `#333d4e` | `#0c1017` | `#181e29` | `#8896ac` | `rgba(120,140,170,0.12)` |
| hist | historical / superseded | `#3a4557` | `#0a0e14` | `#151b25` | `#5d6b81` | `rgba(120,140,170,0.08)` |

Accent hues for header/legend/status: blue `#5b9fd4`, green `#4fb98d`, amber `#c9975a`,
purple `#8f83c9`, historical `#3d4859`.

**Typography**

- UI: `'Plus Jakarta Sans'` 400/500/600/700 (Google Fonts), fallback `ui-sans-serif, system-ui`.
- System metadata only: `'IBM Plex Mono'` 400/500 — step numbers, confidence, raw status,
  ids, timestamps, ROAS multiples.
- Scale: `19px/600` object title · `18px/600` recommendation · `16px/600` key figure ·
  `15.5px/600` node title · `15px/600` product name · `14.5px` inspector value ·
  `14px` body & message text · `13px` secondary/description · `12px` status & type label ·
  `11.5px` edge label · `11px` uppercase group label (`letter-spacing: 0.09em`) ·
  `10px` SYNTHETIC badge (`letter-spacing: 0.08em`).
- Uppercase is used **only** for group labels and the SYNTHETIC badge.

**Spacing scale** — 2, 4, 6, 7, 8, 10, 12, 14, 16, 18, 20, 22, 26 px.
Panel padding `22px`; card padding `14–18px`; section separation `18–26px`;
label→value `2px`; row gap `7–14px`.

**Radii** — `2px` status square · `8px` step row / button · `10px` node card, tinted
sub-surface, legend · `12px` message bubble, evidence card · `50%` timeline dot.

**Shadows** — none by default. Focus ring `0 0 0 1px <border>, 0 0 0 4px <glow>`;
legend popover `0 8px 24px rgba(0,0,0,0.5)`.

---

## Assets

No image assets. All icons are typographic glyphs, chosen for consistency across the app —
reuse the same characters rather than an icon library: `●` active, `○` pending/not observed,
`△` review required / caution, `✓` complete/accepted, `◧` `◨` panel toggles, `−` `+` zoom,
`⛶` fit, `↺` reset. Fonts load from Google Fonts (Plus Jakarta Sans, IBM Plex Mono).

---

## Files

| file | role |
|---|---|
| `AP Intelligence Graph v2.dc.html` | **target design** — open in a browser to interact |
| `AP Intelligence Graph v1.dc.html` | earlier neon iteration, reference only |
| `support.js` | runtime required to open the `.dc.html` files locally |

Production files expected to change (presentation only):
`app/page.tsx` (shell, panel sizing/collapse), `app/globals.css` (theme tokens, keyframes),
`components/IntelligenceGraph.tsx` (spacing, edge styling, progressive labels, drag/zoom),
`components/ApGraphNode.tsx` + `lib/nodeVisuals.ts` (node card content and semantic colors),
`components/ChatPanel.tsx` (workflow steps, message styling),
`components/RecommendationCard.tsx` / `DecisionEvidencePanel.tsx` (grouped evidence hierarchy),
`components/MemoryInspector.tsx` (grouped inspector), `components/ActivityFeed.tsx` (timeline),
`components/ResetDemoButton.tsx` (quiet header treatment).
