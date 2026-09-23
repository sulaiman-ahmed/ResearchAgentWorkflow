"""SQLAlchemy ORM models for Phase B.

Tables added here (Step 05):
  experiments, samples, sample_aliases, result_uploads,
  events, agent_runs, run_steps

Measurements and import_proposals are added in Step 15.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from minibench.db import Base

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExperimentStatus(enum.StrEnum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"


class UploadStatus(enum.StrEnum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class RunState(enum.StrEnum):
    queued = "queued"
    running = "running"
    waiting_approval = "waiting_approval"
    retry_wait = "retry_wait"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    assay_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Flexible conditions (pH, temperature, etc.) stored as JSONB
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus, name="experiment_status"),
        nullable=False,
        default=ExperimentStatus.draft,
    )
    # Fixture-label outcomes — recorded data, not inferred facts
    recorded_outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_step: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    uploads: Mapped[list[ResultUpload]] = relationship("ResultUpload", back_populates="experiment")


# ---------------------------------------------------------------------------
# Samples
# ---------------------------------------------------------------------------


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    aliases: Mapped[list[SampleAlias]] = relationship(
        "SampleAlias", back_populates="sample", cascade="all, delete-orphan"
    )


class SampleAlias(Base):
    __tablename__ = "sample_aliases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sample_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("samples.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)

    sample: Mapped[Sample] = relationship("Sample", back_populates="aliases")

    __table_args__ = (
        # One alias per sample (but the same alias string can appear on multiple samples)
        UniqueConstraint("sample_id", "alias", name="uq_sample_aliases_sample_alias"),
    )


# ---------------------------------------------------------------------------
# Result uploads
# ---------------------------------------------------------------------------


class ResultUpload(Base):
    __tablename__ = "result_uploads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("experiments.id", ondelete="RESTRICT"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False, default="text/csv")
    byte_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="upload_status"),
        nullable=False,
        default=UploadStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="uploads")

    __table_args__ = (
        # Deduplicate byte-identical reuploads to the same experiment
        UniqueConstraint("experiment_id", "sha256", name="uq_result_uploads_experiment_sha256"),
    )


# ---------------------------------------------------------------------------
# Events (immutable envelope)
# ---------------------------------------------------------------------------


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Full immutable payload stored as JSONB
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    runs: Mapped[list[AgentRun]] = relationship("AgentRun", back_populates="event")

    __table_args__ = (
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_aggregate", "aggregate_type", "aggregate_id"),
    )


# ---------------------------------------------------------------------------
# Agent runs
# ---------------------------------------------------------------------------


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
    )
    subscription_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[RunState] = mapped_column(
        Enum(RunState, name="run_state"),
        nullable=False,
        default=RunState.queued,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Cumulative budget usage across all attempts
    cumulative_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped[Event] = relationship("Event", back_populates="runs")
    steps: Mapped[list[RunStep]] = relationship(
        "RunStep", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Each (event, subscription) pair dispatches exactly once
        UniqueConstraint("event_id", "subscription_id", name="uq_agent_runs_event_subscription"),
        Index("ix_agent_runs_state_next_attempt", "state", "next_attempt_at"),
    )


# ---------------------------------------------------------------------------
# Run steps
# ---------------------------------------------------------------------------


class RunStep(Base):
    __tablename__ = "run_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Sanitized inputs/outputs — never raw secrets or full model responses
    inputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    outputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Versions for reproducibility
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    run: Mapped[AgentRun] = relationship("AgentRun", back_populates="steps")

    __table_args__ = (Index("ix_run_steps_run_attempt", "run_id", "attempt", "ordinal"),)


# ---------------------------------------------------------------------------
# Numeric precision constant (used in Step 15 for measurements)
# ---------------------------------------------------------------------------

NUMERIC_PRECISION = Numeric(precision=20, scale=6, asdecimal=True)
