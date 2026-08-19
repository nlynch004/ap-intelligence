"""Deterministic fallback provider - used whenever OPENAI_API_KEY is absent.

This is not a stub that no-ops: it implements real (if simple) rule-based
NLU tuned to the rehearsed demo script in spec Sec.19, so the full loop
(Scenes 1-6) is genuinely demoable with zero API calls. Swapping in a real
OpenAI key later changes nothing about the app's behavior contract - only
the generality/quality of extraction and prose (see llm/factory.py).
"""

from typing import Any

from app.formatting import extract_dollar_amount
from app.llm.provider import LLMProvider


class MockProvider(LLMProvider):
    name = "mock_deterministic"

    def extract_claims(
        self,
        message: str,
        client_id: str,
        client_name: str,
        known_predicates: list[str] | None = None,
        known_partners: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        # known_partners unused: this deterministic fallback only ever
        # extracts the three canned client-level claims from the demo
        # script's Step 2 message (see module docstring) - it never produces
        # a creator/publisher-subject claim, so there's nothing to resolve
        # a partner id for. Accepted here only to keep the same call
        # signature as the live provider (factory.call_with_fallback calls
        # whichever provider is active with identical args).
        text = message.lower()
        candidates: list[dict[str, Any]] = []

        wants_less_coupon = "coupon" in text and any(
            kw in text for kw in ["reduce", "less", "de-emphasize", "dependence", "pull back", "pull-back"]
        )
        if wants_less_coupon:
            candidates.append({
                "type": "client_preference",
                "subject_type": "client",
                "subject_id": client_id,
                "subject_label": client_name,
                "predicate": "partnership_strategy",
                "value": "reduce_coupon_dependence",
                "claim_class": "verified_fact",
                "confidence": 0.93,
                "rationale": "Account team stated the client's strategy shifted away from coupon growth.",
            })

        wants_new_customers = any(kw in text for kw in ["new-customer", "new customer", "new customers"])
        if wants_new_customers:
            candidates.append({
                "type": "client_preference",
                "subject_type": "client",
                "subject_id": client_id,
                "subject_label": client_name,
                "predicate": "primary_growth_objective",
                "value": "new_customer_acquisition",
                "claim_class": "verified_fact",
                "confidence": 0.94,
                "rationale": "Account team stated new-customer acquisition is now the priority.",
            })

        accepts_lower_roas = "roas" in text and any(kw in text for kw in ["lower", "short-term", "short term", "dip"])
        if accepts_lower_roas:
            candidates.append({
                "type": "client_preference",
                "subject_type": "client",
                "subject_id": client_id,
                "subject_label": client_name,
                "predicate": "accepts_tradeoff",
                "value": "lower_short_term_roas",
                "claim_class": "account_preference",
                "confidence": 0.85,
                "rationale": "Account team indicated the client will accept lower short-term ROAS for this tradeoff.",
            })

        return candidates

    def recommend(self, question: str, evidence_brief: str, context: dict[str, Any]) -> dict[str, Any]:
        ask = extract_dollar_amount(question) or context.get("campaign_ask") or 6000.0
        base_fee = round((ask * 0.5833) / 100) * 100
        bonus_pct = 10

        has_hypothesis = context.get("has_attribution_hypothesis", False)
        has_pattern = context.get("has_hybrid_pattern", False)

        uncertainties = []
        if has_hypothesis:
            uncertainties.append("Promo-code leakage is suspected but not verified.")

        explanation_parts = []
        if context.get("primary_goal"):
            explanation_parts.append(f"{context['client_name']}'s current objective is {context['primary_goal']}.")
        if context.get("strategy"):
            explanation_parts.append(f"Their strategy is to {context['strategy']}.")
        explanation_parts.append(f"{context.get('partner_name', 'The partner')} has promising prior commerce performance, but the strongest result has unresolved attribution quality.")
        if has_pattern:
            explanation_parts.append("Comparable synthetic AP portfolio decisions performed better under hybrid compensation than flat-fee renewal.")
        explanation = " ".join(explanation_parts)

        return {
            "recommendation": "renegotiate_and_test",
            "recommended_terms": {
                "base_fee": base_fee,
                "performance_bonus_pct": bonus_pct,
                "bonus_basis": "verified_new_customer_revenue",
            },
            "confidence": 0.74,
            "uncertainties": uncertainties,
            "explanation": explanation,
        }

    def review_campaign(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Deterministic rule-based campaign review, tuned to the three
        Phase-1 planning archetypes (Peak Pursuit: strong/clean; Campfire
        Kate: moderate/strategic-fit; Backcountry Ben: weak commerce/strong
        content) plus Summit Sisters' attribution-caution case - not a stub,
        the same "genuinely demoable with zero API calls" bar as the other
        mock methods.

        Metrics are read, never (re)computed - `evidence` already carries
        attributed_roas etc. from app/memory/retrieval.py."""
        partner_id = evidence.get("partner_id", "")
        partner_name = evidence.get("partner_name") or "This partner"
        month_label = evidence.get("month_label") or "this campaign"
        fee = evidence.get("fee")
        revenue = evidence.get("attributed_revenue")
        roas = evidence.get("attributed_roas")
        cautions = evidence.get("measurement_cautions") or []
        comparison = evidence.get("prior_campaign_comparison") or {}
        partner_note = evidence.get("partner_note")
        has_caution = len(cautions) > 0

        if roas is None:
            tier = "unknown"
        elif roas >= 3.0:
            tier = "strong"
        elif roas >= 1.5:
            tier = "moderate"
        else:
            tier = "weak"

        what_worked: list[str] = []
        what_is_uncertain: list[str] = []
        planning_implications: list[str] = []
        candidate_lessons: list[dict[str, Any]] = []

        if revenue is not None and fee and roas is not None:
            what_worked.append(
                f"{partner_name}'s {month_label} campaign is recorded at ${revenue:,.0f} in attributed revenue "
                f"against a ${fee:,.0f} fee ({roas:.2f}x attributed ROAS)."
            )
        if comparison.get("has_prior") and comparison.get("roas_delta") is not None:
            delta = comparison["roas_delta"]
            direction = "up from" if delta > 0 else ("down from" if delta < 0 else "flat versus")
            what_worked.append(f"Attributed ROAS is {direction} the {comparison.get('prior_month_label')} campaign.")

        if has_caution:
            for c in cautions:
                what_is_uncertain.append(c.get("summary") or "A measurement caution is attached to this campaign - unverified, not a confirmed fact.")
        elif tier == "weak":
            what_is_uncertain.append(
                "Attributed ROAS is below 1.5x with clean, unflagged measurement - the open question is direct-response "
                "economics, not attribution quality."
            )
        elif tier in ("strong", "moderate"):
            what_is_uncertain.append("Attributed revenue is not the same as verified incremental revenue; no measurement caution is on file for this campaign.")

        if partner_note:
            what_is_uncertain.append(
                f"Partner-record note (informal, not governed memory): “{partner_note}” "
                "This may be relevant context but has not been reviewed or approved as a governed claim."
            )

        if has_caution:
            planning_implications.append(
                "Any renewal or scale decision should lean on a bonus basis the caution does not call into question "
                "(e.g. verified new-customer revenue), not the raw attributed figure."
            )
        elif tier == "strong":
            planning_implications.append(
                "Performance supports continued or expanded investment; the open planning question is price, not whether the partnership performs."
            )
        elif tier == "moderate":
            planning_implications.append(
                "Commercial performance alone is moderate - whether to continue likely depends as much on strategic fit as on raw ROAS."
            )
        elif tier == "weak":
            planning_implications.append(
                "Direct-response economics are weak; if the relationship continues, it should be justified on grounds other than attributed commerce."
            )

        # candidate_lessons: propose a partner-level performance
        # characterization only when it isn't entangled with an open
        # measurement caution on THIS campaign (Summit Sisters' May 2026
        # attribution hypothesis must stay a hypothesis, not get laundered
        # into a stronger-sounding governed claim - spec Phase 2 test A).
        if tier in ("strong", "weak") and not has_caution and partner_id:
            value = "consistently_strong_direct_response_economics" if tier == "strong" else "weak_direct_response_economics_despite_content_strength"
            candidate_lessons.append({
                "type": "relationship_memory",
                "subject_type": "creator",
                "subject_id": partner_id,
                "subject_label": partner_name,
                "predicate": "partner_performance_pattern",
                "value": value,
                "claim_class": "historical_observation",
                "confidence": 0.7 if tier == "strong" else 0.6,
                "rationale": f"Derived from the {month_label} campaign review (attributed ROAS {roas:.2f}x)." if roas is not None else f"Derived from the {month_label} campaign review.",
            })
        # A genuinely novel concept (audience-fit, not a performance
        # pattern) - deliberately NOT one of the canonical predicates, so it
        # routes to REQUEST_HUMAN_REVIEW rather than being force-fit into
        # partner_performance_pattern (spec Phase 2 test C + memory test
        # "unknown lesson predicate goes to REQUEST_HUMAN_REVIEW").
        if partner_note and "first-time buyer" in partner_note.lower() and partner_id:
            candidate_lessons.append({
                "type": "relationship_memory",
                "subject_type": "creator",
                "subject_id": partner_id,
                "subject_label": partner_name,
                "predicate": "audience_fit",
                "value": "indexes_toward_first_time_buyers",
                "claim_class": "historical_observation",
                "confidence": 0.55,
                "rationale": "Partner-record note suggests an audience skew relevant to a new-customer-acquisition objective, not yet governed memory.",
            })

        caution_note = ", with an open measurement caution" if has_caution else ""
        summary = f"{partner_name}'s {month_label} campaign: {tier} attributed performance{caution_note}."

        return {
            "summary": summary,
            "what_worked": what_worked,
            "what_is_uncertain": what_is_uncertain,
            "planning_implications": planning_implications,
            "candidate_lessons": candidate_lessons,
        }

    def generate_partner_brief(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Deterministic rule-based partner brief - driven entirely by
        evidence field values (never by partner name), so it naturally
        differs across archetypes without hardcoding any of them, and
        naturally reflects whatever governed state actually exists right
        now (spec: "the brief must truthfully differ depending on whether
        that lesson has been approved in the current demo session")."""
        partner = evidence.get("partner") or {}
        name = partner.get("name") or "This partner"
        synthetic = bool(partner.get("synthetic"))
        stats = evidence.get("performance_stats") or {}
        cautions = evidence.get("measurement_cautions") or []
        client_context = evidence.get("client_context") or []
        decisions = evidence.get("prior_decisions") or []
        outcomes = evidence.get("outcomes") or []
        team = evidence.get("team_experience") or []
        relationship_history = evidence.get("relationship_history") or []
        has_caution = len(cautions) > 0
        avg_roas = stats.get("average_roas")
        campaign_count = stats.get("campaign_count", 0)

        if avg_roas is None:
            tier = "unknown"
        elif avg_roas >= 3.0:
            tier = "strong"
        elif avg_roas >= 1.5:
            tier = "moderate"
        else:
            tier = "weak"

        # --- relationship_summary: WORKED_WITH and negotiation_history are
        # kept as two distinct facts, never merged into "X is the expert."
        worked_with_names = [t["name"] for t in team if t.get("worked_with")]
        documented_negotiation = [h for h in relationship_history if h.get("predicate") == "negotiation_history"]
        rel_parts = []
        if worked_with_names:
            rel_parts.append(f"{' and '.join(sorted(set(worked_with_names)))} has previously worked with {name} (recorded relationship, not evaluated expertise).")
        else:
            rel_parts.append(f"No AP team member is on record as having worked with {name} yet.")
        if documented_negotiation:
            rel_parts.append("There is documented negotiation history on file.")
        else:
            rel_parts.append("No documented negotiation history is on file yet.")
        relationship_summary = " ".join(rel_parts)

        # --- performance_summary: reads performance_stats only, never recomputes.
        if campaign_count == 0:
            performance_summary = f"No campaign history is on file for {name} yet."
        else:
            performance_summary = (
                f"{campaign_count} campaign(s) on file. Most recent attributed ROAS "
                f"{stats.get('most_recent_roas')}x; average across all campaigns {stats.get('average_roas')}x."
            )
            if stats.get("revenue_trend"):
                performance_summary += f" Attributed revenue trend: {stats['revenue_trend']}."

        what_to_know: list[str] = []
        if synthetic:
            what_to_know.append(f"{name} is a synthetic demo partner - all figures are illustrative, not real client data.")
        avg_engagement = stats.get("average_engagement_rate")
        if tier == "strong":
            what_to_know.append("Attributed performance has been consistently strong across the campaigns on file.")
        elif tier == "weak":
            if avg_engagement is not None and avg_engagement >= 0.08:
                what_to_know.append(
                    f"Strong engagement (avg {avg_engagement:.1%}) with weak observed direct-response economics - "
                    "an observed pattern, not a causal claim about why, and not evidence of brand lift."
                )
            else:
                what_to_know.append("Direct-response attributed economics have been weak - an observed pattern, not a causal claim about why.")
        elif tier == "moderate":
            what_to_know.append("Attributed commercial performance has been moderate.")
        if partner.get("partner_note"):
            what_to_know.append(f"Partner-record note (informal, not governed memory): “{partner['partner_note']}”")
        if decisions:
            latest = decisions[-1]
            what_to_know.append(f"A prior decision is on file: {latest['summary'].replace('_', ' ')}.")
        if outcomes:
            latest_outcome = outcomes[-1]
            status_word = "simulated" if latest_outcome.get("is_simulated") else "observed"
            what_to_know.append(f"A {status_word} outcome is on file, labeled {latest_outcome.get('outcome_label')}.")

        negotiation_considerations: list[str] = []
        if has_caution:
            negotiation_considerations.append("Any terms discussion should lean on a metric the open measurement caution does not call into question, not the disputed figure itself.")
        if stats.get("fee_change_pct") is not None:
            direction = "up" if stats["fee_change_pct"] > 0 else ("down" if stats["fee_change_pct"] < 0 else "flat")
            negotiation_considerations.append(f"Fee has moved {direction} {abs(stats['fee_change_pct']):.1f}% from the first campaign on file to the most recent.")
        if not decisions:
            negotiation_considerations.append("There is no prior AP decision on file for this partner to anchor terms against.")

        measurement_considerations: list[str] = []
        if has_caution:
            for c in cautions:
                measurement_considerations.append(c.get("summary") or "A measurement caution is on file - unverified, not a confirmed fact.")
        else:
            measurement_considerations.append("No open measurement caution is on file for this partner's campaigns.")

        open_questions: list[str] = []
        if not decisions:
            open_questions.append(f"What fee or terms is {name} currently requesting?")
        if partner.get("kind") == "creator" and not partner.get("follower_tier"):
            open_questions.append("What is this creator's current follower/audience size?")
        if not client_context:
            open_questions.append("Has Northwind's current strategy been confirmed as still active before this conversation?")

        planning_implications: list[str] = []
        goal_values = [c["value"] for c in client_context if c.get("predicate") == "primary_growth_objective"]
        if goal_values:
            planning_implications.append(f"Northwind's current primary objective is {goal_values[0].replace('_', ' ')} - weigh this partner's fit against that before the conversation.")
        strategy_values = [c["value"] for c in client_context if c.get("predicate") == "partnership_strategy"]
        if strategy_values:
            planning_implications.append(f"Current partnership strategy on file: {strategy_values[0].replace('_', ' ')}.")

        return {
            "relationship_summary": relationship_summary,
            "performance_summary": performance_summary,
            "what_to_know": what_to_know,
            "negotiation_considerations": negotiation_considerations,
            "measurement_considerations": measurement_considerations,
            "open_questions": open_questions,
            "planning_implications": planning_implications,
        }

    def summarize_history(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Deterministic rule-based history narration. Only ever describes
        transitions and cites source info that is actually present in each
        entry - never invents a reason (spec Phase 4: "If the reason for a
        change is not stored, say the reason is not captured.")."""
        entries = evidence.get("entries") or []
        subject_name = evidence.get("subject_name") or "This subject"
        predicate_label = (evidence.get("predicate") or "belief").replace("_", " ")
        current_id = evidence.get("current_claim_id")

        if len(entries) <= 1:
            if entries:
                current_state = f"{subject_name}'s {predicate_label} is currently {entries[0]['value'].replace('_', ' ')}."
            else:
                current_state = f"No governed {predicate_label} is on file for {subject_name} yet."
            return {
                "summary": f"No governed change history exists for {subject_name}'s {predicate_label} yet.",
                "material_changes": [],
                "current_state": current_state,
                "historical_context": [],
            }

        material_changes = [
            f"{entries[i - 1]['value'].replace('_', ' ')} → {entries[i]['value'].replace('_', ' ')}"
            for i in range(1, len(entries))
        ]

        historical_context = []
        for e in entries:
            source = e.get("source") or {}
            if source.get("message_excerpt"):
                detail = f'account statement: "{source["message_excerpt"]}"'
            elif source.get("type"):
                detail = f"source: {source['type']}; reason not captured beyond that"
            else:
                detail = "source/reason not captured"
            historical_context.append(f"{e['value'].replace('_', ' ')} ({e['status']}) - {detail}")

        current = next((e for e in entries if e.get("claim_id") == current_id), entries[-1])
        current_state = f"{subject_name}'s current {predicate_label} is {current['value'].replace('_', ' ')}."
        summary = (
            f"{subject_name}'s {predicate_label} has changed {len(entries) - 1} time"
            f"{'s' if len(entries) - 1 != 1 else ''}: {'; then '.join(material_changes)}."
        )

        return {
            "summary": summary,
            "material_changes": material_changes,
            "current_state": current_state,
            "historical_context": historical_context,
        }

    def compare_scenarios(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Deterministic rule-based scenario comparison. Picks a preferred
        option purely by ranking the application-supplied qualitative
        ratings (never inventing new ones), and only ever names a scenario
        id that was actually supplied - the same guarantee the validated
        fallback in agents/scenario_comparison_agent.py enforces for the
        live provider too."""
        items = evidence.get("scenarios") or []
        partner_name = (evidence.get("partner") or {}).get("name") or "this partner"
        cautions = evidence.get("measurement_cautions") or []
        has_caution = len(cautions) > 0
        client_context = evidence.get("client_context") or []

        rank = {"strong": 2, "moderate": 1, "weak": 0, "high": 0, "low": 2, "unknown": 1}

        def combined_rank(item: dict) -> int:
            a = item["assessment"]
            return rank.get(a["strategy_alignment"], 1) + rank.get(a["measurement_alignment"], 1) + rank.get(a["relationship_continuity"], 1)

        best = max(items, key=combined_rank) if items else None
        preferred_id = best["scenario"]["id"] if best else "do_not_renew"

        tradeoffs = []
        for item in items:
            s, a = item["scenario"], item["assessment"]
            change = f" ({a['change_vs_latest_fee_pct']:+.1f}% vs latest fee)" if a["change_vs_latest_fee_pct"] is not None else ""
            tradeoffs.append(
                f"{s['label']}: {a['compensation_structure']} structure, ${a['guaranteed_spend']:,.0f} guaranteed{change}. "
                f"Strategy alignment {a['strategy_alignment']}, measurement alignment {a['measurement_alignment']}, "
                f"measurement exposure {a['measurement_exposure']}, relationship continuity {a['relationship_continuity']}."
            )

        uncertainties = []
        questions = []
        if has_caution:
            uncertainties.append(
                "An open measurement caution affects how confidently attributed performance can justify a higher guaranteed fee."
            )
            questions.append("Should the measurement caution be resolved before committing to a higher guaranteed fee?")
        if not client_context:
            questions.append(f"Has Northwind's current strategy toward {partner_name} been confirmed as still active?")
        if not questions:
            questions.append("What terms would make each option acceptable to both sides?")

        summary = (
            f"Among the {len(items)} supplied options for {partner_name}, "
            f"{best['scenario']['label'].lower() if best else 'no option'} is most aligned with the current "
            f"strategy and measurement evidence on file."
            if best else f"No scenario evidence was supplied for {partner_name}."
        )

        return {
            "preferred_scenario_id": preferred_id,
            "comparison_summary": summary,
            "tradeoffs": tradeoffs,
            "uncertainties": uncertainties,
            "questions_before_finalizing": questions,
            "confidence": 0.6 if has_caution else 0.72,
        }

    def propose_plan(self, context: dict[str, Any]) -> dict[str, Any]:
        """Deterministic rule-based plan proposal, driven entirely by
        PlanningContext field values (never by partner name) - like
        generate_partner_brief above, this naturally differs per partner
        without hardcoding any of them. Prefers a partner's already-produced
        scenario-comparison result when present (spec Sec.35), otherwise
        falls back to the same performance-tier/measurement-caution reading
        every other mock method already uses. Skips a partner entirely when
        there isn't enough campaign evidence to ground an action (spec
        Sec.10/18), and skips proposing a duplicate of an already-open
        action (spec Sec.9/31) - the application enforces both rules again
        independently, but the mock should not be a bad citizen either."""
        client = context.get("client") or {}
        client_name = client.get("client_name") or "This client"
        period = context.get("planning_period")
        plan_name = f"{client_name} {period} Creator Plan" if period else f"{client_name} Creator Plan"

        strategy = context.get("client", {}).get("current_strategy") or []
        objective_values = [c["value"] for c in strategy if c.get("predicate") == "primary_growth_objective"]
        if objective_values:
            objective = f"Align near-term creator actions with {client_name}'s current primary objective: {objective_values[0].replace('_', ' ')}."
        else:
            objective = f"Establish next-step creator actions for {client_name} from current campaign evidence and governed strategy."

        existing_open = context.get("existing_open_actions") or []

        def is_duplicate(partner_id: str, action_type: str) -> bool:
            return any(a["partner_id"] == partner_id and a["action_type"] == action_type for a in existing_open)

        proposed_actions: list[dict[str, Any]] = []
        for p in context.get("partners") or []:
            partner = p.get("partner") or {}
            partner_id = partner.get("partner_id")
            name = partner.get("name") or partner_id
            stats = p.get("performance_stats") or {}
            cautions = p.get("measurement_cautions") or []
            has_caution = len(cautions) > 0
            scenario = p.get("scenario")
            campaign_count = stats.get("campaign_count", 0)
            avg_roas = stats.get("average_roas")
            avg_engagement = stats.get("average_engagement_rate")

            if campaign_count == 0:
                continue  # not enough evidence to ground an action for this partner

            if avg_roas is None:
                tier = "unknown"
            elif avg_roas >= 3.0:
                tier = "strong"
            elif avg_roas >= 1.5:
                tier = "moderate"
            else:
                tier = "weak"

            supporting_memory_ids = [c["claim_id"] for c in cautions] + [c["claim_id"] for c in (p.get("partner_memory") or [])[:2]]
            supporting_campaign_ids = [c["campaign_id"] for c in (p.get("campaigns") or [])[-2:]]
            source_scenario_id = None

            if scenario:
                preferred_id = scenario.get("preferred_scenario_id")
                preferred = next((s for s in (scenario.get("scenarios") or []) if s["scenario"]["id"] == preferred_id), None)
                preferred_type = preferred["scenario"]["type"] if preferred else None
                action_type = {"do_not_renew": "pause", "hybrid": "renegotiate", "flat_fee": "renew"}.get(preferred_type, "follow_up")
                comparison_summary = scenario.get("comparison_summary", "")
                rationale = f"Grounded in the scenario comparison already produced for {name}: {comparison_summary}"
                source_scenario_id = preferred_id
            elif has_caution:
                action_type = "review_measurement"
                rationale = (
                    f"{name} has an open measurement caution ({cautions[0].get('summary', 'unverified hypothesis')}) - "
                    "resolving it should come before committing to new guaranteed terms."
                )
            elif tier == "strong":
                action_type = "renew"
                rationale = (
                    f"{name}'s attributed performance has been consistently strong (average {avg_roas:.2f}x ROAS across "
                    f"{campaign_count} campaign(s)) with no open measurement caution."
                )
            elif tier == "moderate":
                action_type = "test"
                fit = f" testing further may clarify fit with {client_name}'s current {objective_values[0].replace('_', ' ')} objective before a larger commitment." if objective_values else " worth a further test before a larger commitment."
                rationale = f"{name}'s commercial performance is moderate (average {avg_roas:.2f}x ROAS);{fit}"
            elif tier == "weak":
                if avg_engagement is not None and avg_engagement >= 0.08:
                    action_type = "test"
                    rationale = (
                        f"{name}'s attributed direct-response economics are weak (average {avg_roas:.2f}x ROAS) but engagement is "
                        f"comparatively strong (avg {avg_engagement:.1%}) - worth one bounded test rather than an outright pause."
                    )
                else:
                    action_type = "pause"
                    rationale = (
                        f"{name}'s attributed direct-response economics have been weak (average {avg_roas:.2f}x ROAS across "
                        f"{campaign_count} campaign(s)) with no offsetting engagement signal on file."
                    )
            else:
                action_type = "follow_up"
                rationale = f"Insufficient performance evidence on file for {name} to ground a stronger action yet."

            if is_duplicate(partner_id, action_type):
                continue

            summary_verb = {
                "renew": "Renew", "renegotiate": "Renegotiate", "test": "Run a bounded test with",
                "expand": "Expand investment in", "pause": "Pause", "review_measurement": "Resolve the open measurement question for",
                "follow_up": "Follow up with",
            }[action_type]
            tail = " using a hybrid compensation structure." if action_type == "renegotiate" and scenario else "."
            summary = f"{summary_verb} {name}{tail}"

            proposed_actions.append({
                "partner_id": partner_id, "action_type": action_type, "summary": summary, "rationale": rationale,
                "supporting_memory_ids": supporting_memory_ids, "supporting_campaign_ids": supporting_campaign_ids,
                "source_scenario_id": source_scenario_id,
            })

        return {"plan_name": plan_name, "objective": objective, "proposed_actions": proposed_actions}

    def summarize(self, client_name: str, active_claims: list[dict[str, Any]]) -> str:
        if not active_claims:
            return f"No active memory found yet for {client_name}."
        lines = [f"Here's what AP currently knows about {client_name}:"]
        for c in active_claims:
            lines.append(f"- {c['predicate'].replace('_', ' ')}: {c['value'].replace('_', ' ')}")
        return "\n".join(lines)
