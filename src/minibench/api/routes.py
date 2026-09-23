"""API routes for samples and experiments."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from minibench.api.auth import Principal, require_any, require_reviewer
from minibench.db import get_db
from minibench.domain.models.tables import Sample
from minibench.domain.schemas.contracts import (
    ExperimentCreate,
    ExperimentRead,
    ExperimentUpdate,
    SampleCreate,
    SampleRead,
)
from minibench.domain.services.domain_service import (
    create_experiment,
    create_sample,
    get_experiment,
    get_sample,
    list_experiments,
    list_samples,
    update_experiment,
)

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]
AnyPrincipal = Annotated[Principal, Depends(require_any)]
ReviewerPrincipal = Annotated[Principal, Depends(require_reviewer)]


def _sample_read(sample: Sample) -> SampleRead:
    return SampleRead(
        id=sample.id,
        canonical_code=sample.canonical_code,
        label=sample.label,
        version=sample.version,
        aliases=[a.alias for a in sample.aliases],
    )


# ---------------------------------------------------------------------------
# Samples
# ---------------------------------------------------------------------------


@router.get("/api/samples", response_model=list[SampleRead])
async def list_samples_route(
    db: DbDep,
    _principal: AnyPrincipal,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[SampleRead]:
    samples = await list_samples(db, limit=limit, offset=offset)
    return [_sample_read(s) for s in samples]


@router.post("/api/samples", response_model=SampleRead, status_code=status.HTTP_201_CREATED)
async def create_sample_route(
    body: SampleCreate,
    db: DbDep,
    _principal: ReviewerPrincipal,
) -> SampleRead:
    try:
        sample = await create_sample(db, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return _sample_read(sample)


@router.get("/api/samples/{sample_id}", response_model=SampleRead)
async def get_sample_route(
    sample_id: str,
    db: DbDep,
    _principal: AnyPrincipal,
) -> SampleRead:
    sample = await get_sample(db, sample_id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    return _sample_read(sample)


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


@router.get("/api/experiments", response_model=list[ExperimentRead])
async def list_experiments_route(
    db: DbDep,
    _principal: AnyPrincipal,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ExperimentRead]:
    experiments = await list_experiments(db, limit=limit, offset=offset)
    return [ExperimentRead.model_validate(e) for e in experiments]


@router.post("/api/experiments", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
async def create_experiment_route(
    body: ExperimentCreate,
    db: DbDep,
    principal: AnyPrincipal,
) -> ExperimentRead:
    try:
        experiment = await create_experiment(db, body, actor_id=str(principal))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return ExperimentRead.model_validate(experiment)


@router.get("/api/experiments/{experiment_id}", response_model=ExperimentRead)
async def get_experiment_route(
    experiment_id: str,
    db: DbDep,
    _principal: AnyPrincipal,
) -> ExperimentRead:
    experiment = await get_experiment(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return ExperimentRead.model_validate(experiment)


@router.post("/api/experiments/{experiment_id}/revisions", response_model=ExperimentRead)
async def update_experiment_route(
    experiment_id: str,
    body: ExperimentUpdate,
    db: DbDep,
    principal: ReviewerPrincipal,
) -> ExperimentRead:
    try:
        experiment = await update_experiment(db, experiment_id, body, actor_id=str(principal))
    except ValueError as e:
        detail = str(e)
        code = (
            status.HTTP_409_CONFLICT if "Version conflict" in detail else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail) from e
    return ExperimentRead.model_validate(experiment)
