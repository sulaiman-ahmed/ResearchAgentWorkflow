"""Pydantic create/read contracts for Phase B domain objects.

Separate create and read schemas for each type.
No generic patch endpoints — updates go through explicit versioned commands.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from minibench.domain.models.tables import ExperimentStatus, RunState, UploadStatus

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------


class _ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Sample
# ---------------------------------------------------------------------------


class SampleCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    canonical_code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    metadata_: dict = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class SampleRead(_ReadModel):
    id: str
    canonical_code: str
    label: str
    version: int
    aliases: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------


class ExperimentCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    target_id: str = Field(min_length=1, max_length=64)
    assay_type: str = Field(min_length=1, max_length=64)
    conditions: dict = Field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.draft
    recorded_outcome: str | None = None
    failure_step: str | None = None


class ExperimentUpdate(BaseModel):
    """Explicit versioned update — requires current version to prevent conflicts."""

    expected_version: int
    name: str | None = None
    status: ExperimentStatus | None = None
    recorded_outcome: str | None = None
    failure_step: str | None = None
    conditions: dict | None = None


class ExperimentRead(_ReadModel):
    id: str
    name: str
    target_id: str
    assay_type: str
    conditions: dict
    status: ExperimentStatus
    recorded_outcome: str | None
    failure_step: str | None
    version: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Result upload
# ---------------------------------------------------------------------------


class ResultUploadRead(_ReadModel):
    id: str
    experiment_id: str
    original_filename: str
    storage_key: str | None
    sha256: str | None
    media_type: str
    byte_count: int | None
    status: UploadStatus
    created_at: datetime


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class EventRead(_ReadModel):
    id: str
    event_type: str
    schema_version: int
    aggregate_type: str
    aggregate_id: str
    aggregate_version: int
    actor_id: str | None
    payload: dict
    correlation_id: str | None
    causation_id: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Agent run
# ---------------------------------------------------------------------------


class RunStepRead(_ReadModel):
    id: str
    run_id: str
    attempt: int
    ordinal: int
    kind: str
    started_at: datetime | None
    finished_at: datetime | None
    inputs: dict
    outputs: dict
    error: str | None
    model_id: str | None
    prompt_version: str | None
    tool_name: str | None


class AgentRunRead(_ReadModel):
    id: str
    event_id: str
    subscription_id: str
    agent_version: str
    state: RunState
    attempt_count: int
    next_attempt_at: datetime | None
    worker_id: str | None
    lease_token: str | None
    lease_expires_at: datetime | None
    cumulative_usage: dict
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    steps: list[RunStepRead] = Field(default_factory=list)
