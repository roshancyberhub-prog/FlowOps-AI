from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, now


class EmailDraft(Base):
    __tablename__ = "email_drafts"
    __table_args__ = (UniqueConstraint("execution_id", "node_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    lead_id: Mapped[UUID | None] = mapped_column(ForeignKey("leads.id"), index=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_executions.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(64))
    recipient: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(4000))
    qualification: Mapped[dict] = mapped_column(JSONB)
    provided_facts: Mapped[dict] = mapped_column(JSONB)
    ai_metadata: Mapped[dict] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending_review")
    last_edited_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (UniqueConstraint("execution_id", "node_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_executions.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(64))
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("email_drafts.id"))
    approval_id: Mapped[UUID] = mapped_column(ForeignKey("approval_requests.id"))
    recipient: Mapped[str] = mapped_column(String(320))
    idempotency_key: Mapped[str] = mapped_column(String(150), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(30))
    provider_message_id: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30))
    delivery_metadata: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
