import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class Partner(Base):

    __tablename__ = "partners"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    platform: Mapped[str | None] = mapped_column(String, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    primary_client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    client_id: Mapped[str] = mapped_column(String, ForeignKey("clients.id"))
    partner_id: Mapped[str] = mapped_column(String, ForeignKey("partners.id"))
    month: Mapped[str] = mapped_column(String)
    flat_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagements: Mapped[int | None] = mapped_column(Integer, nullable=True)
    link_clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attributed_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class MemoryClaim(Base):

    __tablename__ = "memory_claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)
    subject_id: Mapped[str] = mapped_column(String)
    predicate: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    client_id: Mapped[str | None] = mapped_column(String, ForeignKey("clients.id"), nullable=True)
    claim_class: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    authority_score: Mapped[float] = mapped_column(Float)
    source: Mapped[dict] = mapped_column(JSON, default=dict)
    valid_from: Mapped[str] = mapped_column(String)
    valid_to: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    supersedes: Mapped[list] = mapped_column(JSON, default=list)
    superseded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MemoryEdge(Base):
    __tablename__ = "memory_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    from_type: Mapped[str] = mapped_column(String)
    from_id: Mapped[str] = mapped_column(String)
    to_type: Mapped[str] = mapped_column(String)
    to_id: Mapped[str] = mapped_column(String)
    relationship: Mapped[str] = mapped_column(String)
    client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MemoryCandidate(Base):

    __tablename__ = "memory_candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String, ForeignKey("clients.id"))
    claim_payload: Mapped[dict] = mapped_column(JSON)
    proposed_operation: Mapped[str] = mapped_column(String)
    conflict_with_claim_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    source_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String, default="chat")
    origin_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String, ForeignKey("clients.id"))
    partner_id: Mapped[str] = mapped_column(String, ForeignKey("partners.id"))
    decision_type: Mapped[str] = mapped_column(String, default="creator_renewal")
    summary: Mapped[str] = mapped_column(Text)
    terms: Mapped[dict] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text)
    motivated_by_claim_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="approved")
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    source_planned_action_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    decision_id: Mapped[str] = mapped_column(String, ForeignKey("decisions.id"))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome_label: Mapped[str] = mapped_column(String)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PortfolioPattern(Base):
    __tablename__ = "portfolio_patterns"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    predicate: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    evidence_count: Mapped[int] = mapped_column(Integer)
    positive_outcomes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flat_fee_success_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    hybrid_success_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    strongest_conditions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="candidate_pattern")
    supporting_decision_ids: Mapped[list] = mapped_column(JSON, default=list)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class Plan(Base):

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(String, ForeignKey("clients.id"))
    name: Mapped[str] = mapped_column(String)
    planning_period: Mapped[str | None] = mapped_column(String, nullable=True)
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="approved")
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PlannedAction(Base):

    __tablename__ = "planned_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("plans.id"))
    client_id: Mapped[str] = mapped_column(String, ForeignKey("clients.id"))
    partner_id: Mapped[str | None] = mapped_column(String, ForeignKey("partners.id"), nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(String, ForeignKey("campaigns.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[str | None] = mapped_column(String, ForeignKey("team_members.id"), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="approved")
    supporting_memory_ids: Mapped[list] = mapped_column(JSON, default=list)
    supporting_campaign_ids: Mapped[list] = mapped_column(JSON, default=list)
    source_scenario_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_decision_id: Mapped[str | None] = mapped_column(String, nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RawEvent(Base):

    __tablename__ = "raw_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ActivityEvent(Base):

    __tablename__ = "activity_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    client_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
