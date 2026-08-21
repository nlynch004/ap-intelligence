from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agents.recommendation_agent import generate_recommendation
from app.db import get_db
from app.formatting import extract_dollar_amount, extract_planning_period, parse_month_mention
from app.llm.factory import call_with_fallback
from app.memory.manager import (
    propose_candidates_from_message,
    propose_plan,
    run_campaign_review,
    run_memory_history,
    run_partner_brief,
    run_scenario_comparison,
    run_what_changed_summary,
)
from app.memory.retrieval import active_client_memories, build_recommendation_context, resolve_historical_predicate
from app.serializers import candidate_to_out

router = APIRouter(prefix="/api", tags=["chat"])

_UP_TO_SPEED_KEYWORDS = ["bring me up to speed", "up to speed", "catch me up", "where do things stand"]


def _matched_partner(db: Session, client_id: str, text: str) -> models.Partner | None:
    lowered = text.lower()
    partners = (
        db.query(models.Partner)
        .join(models.Campaign, models.Campaign.partner_id == models.Partner.id)
        .filter(models.Campaign.client_id == client_id)
        .distinct()
        .all()
    )
    for p in partners:
        if p.name.lower() in lowered:
            return p
    return None


def _looks_like_decision_question(text: str) -> bool:
    lowered = text.lower()
    return "$" in text or any(kw in lowered for kw in ["renew", "should we", "worth renewing", "renegotiat"])


def _looks_like_campaign_review_question(text: str) -> bool:
    lowered = text.lower()
    return "campaign" in lowered and any(kw in lowered for kw in ["review", "how did", "how'd", "how has"])


def _looks_like_partner_brief_question(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in [
        "what should i know", "before i speak", "before speaking",
        "partner brief", "brief for", "help me prepare", "prepare for",
    ])


def _looks_like_scenario_comparison_question(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in ["compare", "scenario", "flat vs", "vs hybrid", "vs not renew", "options for"])


def _looks_like_plan_request(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in [
        "build a plan", "build the plan", "build plan", "build a creator plan", "build our plan",
        "creator plan", "account plan", "next plan", "build northwind's",
    ])


def _looks_like_historical_question(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in [
        "how has", "how did", "what changed", "changed in", "changed with",
        "changed?", "used to", "before the current", "evolve", "evolved",
        "why did", "why has", "what did we believe", "what did northwind believe",
        "view of", "history of",
    ])


def _matched_campaign(db: Session, client_id: str, partner: models.Partner, text: str) -> models.Campaign | None:
    campaigns = (
        db.query(models.Campaign)
        .filter(models.Campaign.partner_id == partner.id, models.Campaign.client_id == client_id)
        .all()
    )
    month = parse_month_mention(text)
    if month:
        for c in campaigns:
            if c.month == month:
                return c
        return None
    return campaigns[0] if len(campaigns) == 1 else None


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    client = db.get(models.Client, req.client_id)
    if not client:
        raise HTTPException(404, "client not found")

    text = req.message.strip()
    lowered = text.lower()

    if any(kw in lowered for kw in _UP_TO_SPEED_KEYWORDS):
        active = active_client_memories(db, req.client_id)
        claim_dicts = [{"predicate": c.predicate, "value": c.value} for c in active]
        summary, _provider = call_with_fallback("summarize", client.name, claim_dicts)
        return schemas.ChatResponse(reply=summary, candidates=[], referenced_memory_ids=[c.id for c in active])

    if _looks_like_plan_request(text):
        planning_period = extract_planning_period(text)
        proposal = propose_plan(db, client_id=req.client_id, planning_period=planning_period)
        if proposal:
            reply = (
                f"Plan proposal — {proposal.plan_name}: {len(proposal.proposed_actions)} proposed action(s) across "
                f"{len({a.partner_id for a in proposal.proposed_actions})} partner(s). Review below before approving any of them."
            )
            return schemas.ChatResponse(reply=reply, candidates=[], referenced_memory_ids=[], plan_proposal=proposal)

    partner = _matched_partner(db, req.client_id, text)

    if partner and _looks_like_scenario_comparison_question(text):
        ask = extract_dollar_amount(text)
        if ask is None:
            reply = (
                f"A current renewal ask is required before comparing renewal economics for {partner.name}. "
                f"What are they currently asking for?"
            )
            return schemas.ChatResponse(reply=reply, candidates=[], referenced_memory_ids=[])
        comparison = run_scenario_comparison(db, client_id=req.client_id, partner_id=partner.id, current_ask=ask)
        if comparison:
            return schemas.ChatResponse(
                reply=f"Scenario comparison — {comparison.evidence.partner.name}: {comparison.comparison_summary}",
                candidates=[], referenced_memory_ids=[], scenario_comparison=comparison,
            )

    if partner and _looks_like_campaign_review_question(text):
        campaign = _matched_campaign(db, req.client_id, partner, text)
        if campaign:
            review = run_campaign_review(db, campaign_id=campaign.id)
            if review:
                return schemas.ChatResponse(
                    reply=f"Campaign review — {review.evidence.partner_name}, {review.evidence.month_label}: {review.summary}",
                    candidates=[], referenced_memory_ids=[], campaign_review=review,
                )

    if _looks_like_historical_question(text):
        subject_type = partner.kind if partner else "client"
        subject_id = partner.id if partner else req.client_id
        predicate = resolve_historical_predicate(text)

        if predicate:
            history = run_memory_history(db, subject_type=subject_type, subject_id=subject_id, predicate=predicate, client_id=req.client_id)
            predicate_label = predicate.replace("_", " ")
            if history is None:
                reply = f"No governed {predicate_label} information is on file for {partner.name if partner else client.name} yet."
                return schemas.ChatResponse(reply=reply, candidates=[], referenced_memory_ids=[])
            if len(history.timeline.changes) <= 1:
                reply = f"No governed change history exists yet for {history.timeline.subject.name}'s {predicate_label}. {history.current_state}"
            else:
                reply = f"{history.timeline.subject.name}'s {predicate_label}: {history.summary}"
            return schemas.ChatResponse(reply=reply, candidates=[], referenced_memory_ids=[], memory_history=history)

        summary = run_what_changed_summary(db, subject_type=subject_type, subject_id=subject_id, client_id=req.client_id)
        if summary.changed_dimensions:
            reply = f"{len(summary.changed_dimensions)} governed belief(s) changed for {summary.subject.name}."
        else:
            reply = f"No governed change history exists for {summary.subject.name} yet."
        return schemas.ChatResponse(reply=reply, candidates=[], referenced_memory_ids=[], what_changed=summary)

    if partner and _looks_like_partner_brief_question(text):
        brief = run_partner_brief(db, partner_id=partner.id, client_id=req.client_id)
        if brief:
            return schemas.ChatResponse(
                reply=f"Partner brief — {brief.evidence.partner.name}: {brief.relationship_summary}",
                candidates=[], referenced_memory_ids=[], partner_brief=brief,
            )

    if partner and _looks_like_decision_question(text):
        ctx = build_recommendation_context(db, client_id=req.client_id, partner_id=partner.id, question=text)
        raw_rec, _provider = generate_recommendation(text, ctx["evidence_brief"], ctx["structured_context"])
        rec = schemas.RecommendationResponse(
            client_id=req.client_id,
            partner_id=partner.id,
            decision_evidence=ctx["decision_evidence"],
            recommendation=raw_rec["recommendation"],
            recommended_terms=raw_rec["recommended_terms"],
            confidence=raw_rec["confidence"],
            supporting_memory_ids=ctx["supporting_memory_ids"],
            uncertainties=raw_rec.get("uncertainties", []),
            explanation=raw_rec.get("explanation", ""),
            evidence_brief=ctx["evidence_brief"],
        )
        reply = f"Recommendation: {raw_rec['recommendation'].replace('_', ' ')}. {raw_rec.get('explanation', '')}"
        return schemas.ChatResponse(reply=reply, candidates=[], referenced_memory_ids=ctx["supporting_memory_ids"], recommendation=rec)

    candidates, _provider = propose_candidates_from_message(db, client_id=req.client_id, message=text)
    db.commit()

    if not candidates:
        return schemas.ChatResponse(reply="Noted - I didn't find anything durable enough to remember from that message.", candidates=[])

    conflicts = {
        c.conflict_with_claim_id: db.get(models.MemoryClaim, c.conflict_with_claim_id)
        for c in candidates if c.conflict_with_claim_id
    }
    candidate_outs = [candidate_to_out(c, conflicts.get(c.conflict_with_claim_id)) for c in candidates]
    reply = f"I found {len(candidates)} potentially useful {'memory' if len(candidates) == 1 else 'memories'}. Review below."
    return schemas.ChatResponse(reply=reply, candidates=candidate_outs, referenced_memory_ids=[])
