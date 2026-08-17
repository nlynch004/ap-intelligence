from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.formatting import format_month
from app.llm.factory import call_with_fallback
from app.memory.retrieval import active_client_memories
from app.serializers import claim_to_out

router = APIRouter(prefix="/api/clients", tags=["graph"])


def node_key(node_type: str, raw_id: str) -> str:
    return f"{node_type}:{raw_id}"


def _resolve_node(db: Session, node_type: str, raw_id: str) -> schemas.GraphNode | None:
    if node_type == "client":
        obj = db.get(models.Client, raw_id)
        if not obj:
            return None
        return schemas.GraphNode(id=node_key(node_type, raw_id), node_type="client", label=obj.name, data={"industry": obj.industry, "synthetic": obj.synthetic})

    if node_type == "partner":
        obj = db.get(models.Partner, raw_id)
        if not obj:
            return None
        return schemas.GraphNode(
            id=node_key(node_type, raw_id), node_type=obj.kind, label=obj.name,
            data={"platform": obj.platform, "synthetic": obj.synthetic, **obj.meta},
        )

    if node_type == "campaign":
        obj = db.get(models.Campaign, raw_id)
        if not obj:
            return None
        partner = db.get(models.Partner, obj.partner_id)
        partner_name = partner.name if partner else obj.partner_id
        # Two-line label ("Summit Sisters" / "May 2026 Campaign") - a bare
        # "2026-05 campaign" is indistinguishable between two creators who
        # both ran a campaign that month (spec Sec.6, Step 4 audit finding).
        # Frontend renders the "\n" as a line break (whitespace-pre-line).
        return schemas.GraphNode(
            id=node_key(node_type, raw_id), node_type="campaign",
            label=f"{partner_name}\n{format_month(obj.month)} Campaign",
            data={
                "flat_fee": obj.flat_fee, "link_clicks": obj.link_clicks,
                "code_redemptions": obj.code_redemptions, "attributed_revenue": obj.attributed_revenue,
                "partner_id": obj.partner_id, "partner_name": partner_name, "month": obj.month,
            },
        )

    if node_type == "team_member":
        obj = db.get(models.TeamMember, raw_id)
        if not obj:
            return None
        return schemas.GraphNode(id=node_key(node_type, raw_id), node_type="team_member", label=obj.name, data={"role": obj.role, "synthetic": obj.synthetic})

    if node_type == "memory_claim":
        obj = db.get(models.MemoryClaim, raw_id)
        if not obj:
            return None
        return schemas.GraphNode(
            id=node_key(node_type, raw_id), node_type="memory_claim",
            label=f"{obj.predicate.replace('_', ' ')}: {obj.value.replace('_', ' ')}",
            status=obj.status,
            data=claim_to_out(obj).model_dump(),
        )

    if node_type == "decision":
        obj = db.get(models.Decision, raw_id)
        if not obj:
            return None
        return schemas.GraphNode(
            id=node_key(node_type, raw_id), node_type="decision", label=obj.summary, status=obj.status,
            data={"terms": obj.terms, "rationale": obj.rationale, "synthetic": obj.synthetic},
        )

    if node_type == "outcome":
        obj = db.get(models.Outcome, raw_id)
        if not obj:
            return None
        return schemas.GraphNode(id=node_key(node_type, raw_id), node_type="outcome", label=f"Outcome: {obj.outcome_label}", status=obj.outcome_label, data={"metrics": obj.metrics, "is_simulated": obj.is_simulated})

    if node_type == "portfolio_pattern":
        obj = db.get(models.PortfolioPattern, raw_id)
        if not obj:
            return None
        return schemas.GraphNode(
            id=node_key(node_type, raw_id), node_type="portfolio_pattern", label=obj.name.replace("_", " "),
            status=obj.status,
            data={
                "description": obj.description, "evidence_count": obj.evidence_count,
                "positive_outcomes": obj.positive_outcomes, "flat_fee_success_rate": obj.flat_fee_success_rate,
                "hybrid_success_rate": obj.hybrid_success_rate, "strongest_conditions": obj.strongest_conditions,
                "synthetic": obj.synthetic,
            },
        )

    return None


@router.get("", response_model=list[dict])
def list_clients(db: Session = Depends(get_db)):
    clients = db.query(models.Client).order_by(models.Client.synthetic, models.Client.name).all()
    return [{"id": c.id, "name": c.name, "industry": c.industry, "synthetic": c.synthetic} for c in clients]


@router.get("/{client_id}/graph", response_model=schemas.GraphResponse)
def get_graph(client_id: str, db: Session = Depends(get_db)):
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(404, "client not found")

    edges = db.query(models.MemoryEdge).filter(models.MemoryEdge.client_id == client_id).all()

    node_refs: set[tuple[str, str]] = {("client", client_id)}
    for e in edges:
        node_refs.add((e.from_type, e.from_id))
        node_refs.add((e.to_type, e.to_id))

    nodes = [n for n in (_resolve_node(db, t, i) for t, i in node_refs) if n is not None]
    graph_edges = [
        schemas.GraphEdge(id=e.id, source=node_key(e.from_type, e.from_id), target=node_key(e.to_type, e.to_id), relationship=e.relationship)
        for e in edges
    ]
    return schemas.GraphResponse(nodes=nodes, edges=graph_edges)


@router.get("/{client_id}/brief", response_model=schemas.ClientBriefResponse)
def get_brief(client_id: str, db: Session = Depends(get_db)):
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(404, "client not found")

    active = active_client_memories(db, client_id)
    claim_dicts = [{"predicate": c.predicate, "value": c.value} for c in active]
    summary, _provider = call_with_fallback("summarize", client.name, claim_dicts)

    return schemas.ClientBriefResponse(
        client_id=client.id, client_name=client.name,
        active_memories=[claim_to_out(c) for c in active],
        summary=summary,
    )
