"""Seed demo data from fixtures.

Usage (runs inside the Compose network, uses the container DB):
    docker compose run --rm api uv run python -m minibench.scripts.seed_demo

Safe to run repeatedly — uses stable fixture IDs, skips existing records.
Development-only: does not trigger live agents or events beyond experiment.created.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from sqlalchemy import select

from minibench.db import AsyncSessionLocal
from minibench.domain.models.tables import Experiment, Sample
from minibench.domain.schemas.contracts import ExperimentCreate, SampleCreate
from minibench.domain.services.domain_service import create_experiment, create_sample


def _load(filename: str) -> list[dict]:
    # Try CWD/fixtures first (works both in container at /app and locally)
    candidates = [
        Path(os.getcwd()) / "fixtures" / filename,
        Path(__file__).parents[4] / "fixtures" / filename,
    ]
    for path in candidates:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
    raise FileNotFoundError(f"fixtures/{filename} not found in {[str(c) for c in candidates]}")


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ----------------------------------------------------------------
        # Samples
        # ----------------------------------------------------------------
        samples_data = _load("samples.json")
        seeded_samples = 0
        for s in samples_data:
            existing = await db.scalar(select(Sample).where(Sample.id == s["id"]))
            if existing:
                continue
            await create_sample(
                db,
                SampleCreate(
                    id=s["id"],
                    canonical_code=s["canonical_code"],
                    label=s["label"],
                    aliases=s.get("aliases", []),
                    metadata=s.get("properties", {}),
                ),
            )
            seeded_samples += 1

        # ----------------------------------------------------------------
        # Experiments
        # ----------------------------------------------------------------
        experiments_data = _load("experiments.json")
        seeded_experiments = 0
        for e in experiments_data:
            existing = await db.scalar(select(Experiment).where(Experiment.id == e["id"]))
            if existing:
                continue
            await create_experiment(
                db,
                ExperimentCreate(
                    id=e["id"],
                    name=e["name"],
                    target_id=e["target_id"],
                    assay_type=e["assay_type"],
                    conditions=e.get("conditions", {}),
                    status=e.get("status", "completed"),
                    recorded_outcome=e.get("recorded_outcome"),
                    failure_step=e.get("failure_step"),
                ),
                actor_id="seed",
            )
            seeded_experiments += 1

        print(f"Seeded {seeded_samples} samples, {seeded_experiments} experiments.")
        print("(Skipped existing records.)")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
