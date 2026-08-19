"""Provider-agnostic LLM interface (spec Sec.23, Sec.21).

Eight bounded methods - the minimum the product needs an LLM for. Everything
else (validation, IDs, state transitions, conflict lookup, retrieval
filtering, all metrics/comparisons) is deterministic application code in
app/memory/, per spec Sec.22: "The model proposes; application logic
validates and persists." `review_campaign` (Phase 2) and `generate_partner_brief`
(Phase 3) follow the same contract as `recommend`: each receives only
pre-computed evidence, never raw DB rows, and never calculates a metric
itself.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def extract_claims(
        self,
        message: str,
        client_id: str,
        client_name: str,
        known_predicates: list[str] | None = None,
        known_partners: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return candidate claim dicts shaped like CandidateClaimPayload.
        Should return an empty list for messages that contain no durable,
        structured, client-relevant fact (do not force claims out of chatter).

        `known_predicates` lists the predicate names already active for this
        client's claims - implementations should be steered to reuse an exact
        match when applicable, since conflict detection downstream is a
        deterministic exact-string match, not semantic (spec Sec.11).

        `known_partners` lists {id, name, kind} for this client's existing
        creators/publishers - implementations should be steered to reuse an
        existing partner's exact id as subject_id when the message names
        them, rather than inventing a new slug for the same entity.
        """

    @abstractmethod
    def recommend(self, question: str, evidence_brief: str, context: dict[str, Any]) -> dict[str, Any]:
        """Return a dict shaped like the recommendation output in spec Sec.20
        (minus supporting_memory_ids, which the deterministic retrieval layer
        attaches itself rather than trusting the model to invent IDs)."""

    @abstractmethod
    def summarize(self, client_name: str, active_claims: list[dict[str, Any]]) -> str:
        """Concise prose summary of currently active memory, for the
        'bring me up to speed' scene."""

    @abstractmethod
    def review_campaign(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Return a dict shaped like schemas.CampaignReviewResponse's
        LLM-authored fields: summary, what_worked, what_is_uncertain,
        planning_implications, candidate_lessons (each shaped like a raw
        extraction claim - see agents/prompts.py). `evidence` is
        schemas.CampaignReviewEvidence.model_dump() - deterministic,
        pre-computed evidence only. Implementations must not calculate
        metrics, claim causal lift, convert attributed revenue into
        incrementality, upgrade a hypothesis into a fact, or persist
        anything - candidate_lessons are proposals, not writes."""

    @abstractmethod
    def generate_partner_brief(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Return a dict shaped like schemas.PartnerBriefResponse's
        LLM-authored fields: relationship_summary, performance_summary,
        what_to_know, negotiation_considerations, measurement_considerations,
        open_questions, planning_implications. `evidence` is
        schemas.PartnerBriefEvidence.model_dump() - deterministic evidence
        only. Implementations must not calculate ROAS or fee changes,
        invent missing partner history/terms/outcomes, claim causal lift or
        brand lift, invent audience demographics, upgrade a hypothesis into
        a fact, infer expertise from a WORKED_WITH edge alone, or persist
        anything - this is read-only preparation (spec Phase 3), not a
        learning loop."""

    @abstractmethod
    def summarize_history(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Return a dict shaped like schemas.MemoryHistoryResponse's
        LLM-authored fields: summary, material_changes, current_state,
        historical_context. `evidence` is the deterministically-ordered
        timeline dict from app/memory/retrieval.py::build_memory_history -
        the model narrates it, it does not determine it. Implementations
        must not invent why a belief changed when no source/reason is
        recorded (say the reason is not captured instead), invent dates,
        rewrite lifecycle status, treat a superseded entry as current, or
        infer causality from timing alone. Read-only - never persists."""

    @abstractmethod
    def compare_scenarios(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """Return a dict shaped like schemas.ScenarioComparisonResponse's
        LLM-authored fields: preferred_scenario_id (must name one of the
        scenario ids in evidence["scenarios"] - an invented id is treated
        as a validation failure, see agents/scenario_comparison_agent.py),
        comparison_summary, tradeoffs, uncertainties,
        questions_before_finalizing, confidence. `evidence` is
        schemas.ScenarioComparisonEvidence.model_dump() - the three
        scenarios and every qualitative rating are already deterministically
        built and assessed (app/memory/scenario_rules.py); this method
        explains and picks among them, it does not construct or rate them.
        Implementations must not invent expected revenue, forecast ROAS,
        calculate any financial metric, claim incrementality or causal
        uplift, invent partner terms, change an application-generated
        rating, upgrade a hypothesis to fact, propose a fourth scenario, or
        persist anything. This is decision support, not forecasting."""

    @abstractmethod
    def propose_plan(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return a dict shaped like schemas.PlanProposalResponse's
        LLM-authored fields: plan_name, objective, proposed_actions (each
        shaped like schemas.ProposedPlannedAction minus temp_id/partner_name/
        duplicate_of_planned_action_id, which the application fills in -
        see app/agents/plan_agent.py and app/memory/planning_rules.py).
        `context` is schemas.PlanningContext.model_dump() - deterministic
        evidence only, including, for some partners, an already-produced
        scenario-comparison result. Implementations must not calculate a
        metric, invent expected revenue or forecast ROAS, claim
        incrementality, invent partner history/terms, propose an action for
        a partner not present in `context`, use an action_type outside the
        seven bounded values, assign an owner or due date, duplicate a
        partner+action_type pair already in `context["existing_open_actions"]`,
        or persist/approve anything - this proposes a draft only; the
        application intersects every id against `context` before anything
        is shown to a human, and nothing here is ever written to the
        database directly."""
