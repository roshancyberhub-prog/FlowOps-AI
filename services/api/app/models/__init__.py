from datetime import datetime
from uuid import UUID, uuid4

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, now
from app.models.execution import ApprovalRequest as ApprovalRequest
from app.models.execution import ExecutionStep as ExecutionStep
from app.models.execution import Notification as Notification
from app.models.execution import OutboxEntry as OutboxEntry
from app.models.execution import WorkerHeartbeat as WorkerHeartbeat
from app.models.execution import WorkflowExecution as WorkflowExecution
from app.models.imports import ImportJob as ImportJob
from app.models.imports import ImportRow as ImportRow
from app.models.outreach import EmailDelivery as EmailDelivery
from app.models.outreach import EmailDraft as EmailDraft
from app.models.scoring import ScoringProfile as ScoringProfile


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    display_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    __tablename__ = "access_tokens"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(150), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Membership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="membership_role"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_lead_organization_email"),
        CheckConstraint("score BETWEEN 0 AND 100", name="lead_score_range"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(320))
    company: Mapped[str | None] = mapped_column(String(200))
    job_title: Mapped[str | None] = mapped_column(String(150))
    website: Mapped[str | None] = mapped_column(String(2048))
    industry: Mapped[str | None] = mapped_column(String(100))
    company_size: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    score: Mapped[int] = mapped_column(default=0)
    score_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    score_profile_id: Mapped[UUID | None] = mapped_column(ForeignKey("scoring_profiles.id"))
    score_profile_version: Mapped[int | None]
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(100))
    correlation_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint("status IN ('draft','active','paused','archived')", name="workflow_status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    scheduled_next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    draft_graph: Mapped[dict] = mapped_column(JSONB)
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workflow_versions.id", use_alter=True, name="fk_workflow_current_version")
    )
    version_number: Mapped[int] = mapped_column(default=0)
    revision: Mapped[int] = mapped_column(default=1)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now, index=True
    )


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version_number"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    version_number: Mapped[int]
    graph_definition: Mapped[dict] = mapped_column(JSONB)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
