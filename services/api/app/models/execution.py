from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, now


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_execution_idempotency"),
        CheckConstraint(
            "status IN ('queued','running','waiting_for_approval',"
            "'retrying','succeeded','failed','cancelled')",
            name="execution_status",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    workflow_version_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_versions.id"))
    workflow_name: Mapped[str] = mapped_column(String(150))
    version_number: Mapped[int]
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    trigger_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    mode: Mapped[str] = mapped_column(String(20), default="test")
    idempotency_key: Mapped[str] = mapped_column(String(200))
    input_hash: Mapped[str] = mapped_column(String(64))
    input_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    current_node_id: Mapped[str | None] = mapped_column(String(64))
    node_attempt: Mapped[int] = mapped_column(default=0)
    dispatch_generation: Mapped[int] = mapped_column(default=0)
    manual_retry_count: Mapped[int] = mapped_column(default=0)
    active_duration_ms: Mapped[int] = mapped_column(default=0)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    lease_token: Mapped[UUID | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    correlation_id: Mapped[str] = mapped_column(String(36))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_summary: Mapped[str | None] = mapped_column(String(500))
    dead_letter: Mapped[bool] = mapped_column(default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ExecutionStep(Base):
    __tablename__ = "execution_steps"
    __table_args__ = (UniqueConstraint("execution_id", "node_id", "attempt_number"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_executions.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(64))
    node_type: Mapped[str] = mapped_column(String(80))
    attempt_number: Mapped[int]
    status: Mapped[str] = mapped_column(String(30), default="running")
    input_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_summary: Mapped[str | None] = mapped_column(String(500))
    error_frames: Mapped[list] = mapped_column(JSONB, default=list)
    retryable: Mapped[bool] = mapped_column(default=False)
    uncertain: Mapped[bool] = mapped_column(default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None]


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (UniqueConstraint("execution_id", "node_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_executions.id"), index=True)
    execution_step_id: Mapped[UUID] = mapped_column(ForeignKey("execution_steps.id"))
    node_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(30), default="email")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    payload_hash: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(default=1)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_comment: Mapped[str] = mapped_column(String(1000), default="")


class OutboxEntry(Base):
    __tablename__ = "outbox_entries"
    __table_args__ = (
        CheckConstraint(
            "(execution_id IS NOT NULL AND import_job_id IS NULL) OR "
            "(execution_id IS NULL AND import_job_id IS NOT NULL)",
            name="outbox_one_target",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workflow_executions.id"), index=True
    )
    import_job_id: Mapped[UUID | None] = mapped_column(ForeignKey("import_jobs.id"), index=True)
    dispatch_key: Mapped[str] = mapped_column(String(100), unique=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    worker_name: Mapped[str] = mapped_column(String(120), unique=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("execution_id", "node_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_executions.id"))
    node_id: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(1000))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
