"""Domain services for Samples and Experiments.

Services contain all business logic. Routes are thin wrappers around these.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from minibench.domain.models.tables import (
    Event,
    Experiment,
    Sample,
    SampleAlias,
)
from minibench.domain.schemas.contracts import ExperimentCreate, ExperimentUpdate, SampleCreate

# ---------------------------------------------------------------------------
# Sample service
# ---------------------------------------------------------------------------


async def create_sample(db: AsyncSession, data: SampleCreate) -> Sample:
    existing = await db.scalar(select(Sample).where(Sample.canonical_code == data.canonical_code))
    if existing:
        raise ValueError(f"Sample with canonical_code '{data.canonical_code}' already exists")

    sample = Sample(
        id=data.id,
        canonical_code=data.canonical_code,
        label=data.label,
        metadata_=data.metadata_,
    )
    db.add(sample)

    for alias_str in data.aliases:
        db.add(SampleAlias(sample_id=data.id, alias=alias_str))

    await db.commit()
    await db.refresh(sample)
    return sample


async def get_sample(db: AsyncSession, sample_id: str) -> Sample | None:
    result = await db.scalar(
        select(Sample).options(selectinload(Sample.aliases)).where(Sample.id == sample_id)
    )
    return result


async def list_samples(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Sample]:
    result = await db.scalars(
        select(Sample).options(selectinload(Sample.aliases)).offset(offset).limit(limit)
    )
    return list(result.all())


# ---------------------------------------------------------------------------
# Experiment service
# ---------------------------------------------------------------------------


async def create_experiment(
    db: AsyncSession, data: ExperimentCreate, actor_id: str = "system"
) -> Experiment:
    experiment = Experiment(
        id=data.id,
        name=data.name,
        target_id=data.target_id,
        assay_type=data.assay_type,
        conditions=data.conditions,
        status=data.status,
        recorded_outcome=data.recorded_outcome,
        failure_step=data.failure_step,
        version=1,
    )
    db.add(experiment)

    # Emit experiment.created event in the same transaction
    event = Event(
        id=f"evt-{data.id}-created",
        event_type="experiment.created",
        schema_version=1,
        aggregate_type="experiment",
        aggregate_id=data.id,
        aggregate_version=1,
        actor_id=actor_id,
        payload={
            "experiment_id": data.id,
            "name": data.name,
            "target_id": data.target_id,
            "assay_type": data.assay_type,
            "conditions": data.conditions,
        },
    )
    db.add(event)

    await db.commit()
    await db.refresh(experiment)
    return experiment


async def get_experiment(db: AsyncSession, experiment_id: str) -> Experiment | None:
    return await db.scalar(select(Experiment).where(Experiment.id == experiment_id))


async def list_experiments(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Experiment]:
    result = await db.scalars(select(Experiment).offset(offset).limit(limit))
    return list(result.all())


async def update_experiment(
    db: AsyncSession,
    experiment_id: str,
    data: ExperimentUpdate,
    actor_id: str = "system",
) -> Experiment:
    experiment = await db.scalar(
        select(Experiment).where(Experiment.id == experiment_id).with_for_update()
    )
    if not experiment:
        raise ValueError(f"Experiment '{experiment_id}' not found")
    if experiment.version != data.expected_version:
        raise ValueError(
            f"Version conflict: expected {data.expected_version}, got {experiment.version}"
        )

    if data.name is not None:
        experiment.name = data.name
    if data.status is not None:
        experiment.status = data.status
    if data.recorded_outcome is not None:
        experiment.recorded_outcome = data.recorded_outcome
    if data.failure_step is not None:
        experiment.failure_step = data.failure_step
    if data.conditions is not None:
        experiment.conditions = data.conditions

    experiment.version += 1
    experiment.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(experiment)
    return experiment
