"""API tests for samples and experiments.

These test the full request/response cycle using FastAPI's TestClient.
They do not require a running database — they test validation, auth,
and routing logic with dependency overrides.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from minibench.db import get_db
from minibench.domain.models.tables import Experiment, ExperimentStatus, Sample
from minibench.main import app
from minibench.settings import settings

REVIEWER_KEY = settings.reviewer_api_key or "test-reviewer"
WORKER_KEY = settings.worker_api_key or "test-worker"
REVIEWER_HEADERS = {"X-Api-Key": REVIEWER_KEY}
WORKER_HEADERS = {"X-Api-Key": WORKER_KEY}
BAD_HEADERS = {"X-Api-Key": "bad-key"}


async def _mock_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override: yields a mock session so no DB connection is needed."""
    yield MagicMock(spec=AsyncSession)


def _client() -> TestClient:
    """TestClient with DB dependency overridden."""
    app.dependency_overrides[get_db] = _mock_db
    return TestClient(app, raise_server_exceptions=False)


def _make_sample(id: str = "s-001", code: str = "SAMP_001") -> Sample:
    s = Sample(id=id, canonical_code=code, label="Test Sample", version=1, metadata_={})
    s.aliases = []
    return s


def _make_experiment(id: str = "exp-001") -> Experiment:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return Experiment(
        id=id,
        name="Test Experiment",
        target_id="PROT_A",
        assay_type="binding",
        conditions={},
        status=ExperimentStatus.draft,
        recorded_outcome=None,
        failure_step=None,
        version=1,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestAuth:
    def test_missing_key_returns_422(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/samples")
            assert resp.status_code == 422

    def test_bad_key_returns_401(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/samples", headers=BAD_HEADERS)
            assert resp.status_code == 401

    def test_worker_key_denied_on_create_sample(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/samples",
                json={"id": "s-001", "canonical_code": "SAMP_001", "label": "x"},
                headers=WORKER_HEADERS,
            )
            assert resp.status_code == 403

    def test_worker_key_denied_on_experiment_revision(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/experiments/exp-001/revisions",
                json={"expected_version": 1, "name": "new name"},
                headers=WORKER_HEADERS,
            )
            assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Sample routes
# ---------------------------------------------------------------------------


class TestSampleRoutes:
    def test_list_samples(self) -> None:
        sample = _make_sample()
        with patch("minibench.api.routes.list_samples", new_callable=AsyncMock) as mock:
            mock.return_value = [sample]
            with _client() as client:
                resp = client.get("/api/samples", headers=REVIEWER_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["canonical_code"] == "SAMP_001"

    def test_get_sample_not_found(self) -> None:
        with patch("minibench.api.routes.get_sample", new_callable=AsyncMock) as mock:
            mock.return_value = None
            with _client() as client:
                resp = client.get("/api/samples/missing", headers=REVIEWER_HEADERS)
        assert resp.status_code == 404

    def test_create_sample_conflict(self) -> None:
        with patch("minibench.api.routes.create_sample", new_callable=AsyncMock) as mock:
            mock.side_effect = ValueError("Sample with canonical_code 'SAMP_001' already exists")
            with _client() as client:
                resp = client.post(
                    "/api/samples",
                    json={"id": "s-001", "canonical_code": "SAMP_001", "label": "x"},
                    headers=REVIEWER_HEADERS,
                )
        assert resp.status_code == 409

    def test_create_sample_invalid_body(self) -> None:
        with _client() as client:
            resp = client.post(
                "/api/samples",
                json={"id": "", "canonical_code": "SAMP_001", "label": "x"},
                headers=REVIEWER_HEADERS,
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Experiment routes
# ---------------------------------------------------------------------------


class TestExperimentRoutes:
    def test_list_experiments(self) -> None:
        exp = _make_experiment()
        with patch("minibench.api.routes.list_experiments", new_callable=AsyncMock) as mock:
            mock.return_value = [exp]
            with _client() as client:
                resp = client.get("/api/experiments", headers=REVIEWER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()[0]["id"] == "exp-001"

    def test_get_experiment_not_found(self) -> None:
        with patch("minibench.api.routes.get_experiment", new_callable=AsyncMock) as mock:
            mock.return_value = None
            with _client() as client:
                resp = client.get("/api/experiments/missing", headers=REVIEWER_HEADERS)
        assert resp.status_code == 404

    def test_create_experiment_returns_201(self) -> None:
        exp = _make_experiment()
        with patch("minibench.api.routes.create_experiment", new_callable=AsyncMock) as mock:
            mock.return_value = exp
            with _client() as client:
                resp = client.post(
                    "/api/experiments",
                    json={
                        "id": "exp-001",
                        "name": "Test",
                        "target_id": "PROT_A",
                        "assay_type": "binding",
                    },
                    headers=REVIEWER_HEADERS,
                )
        assert resp.status_code == 201

    def test_update_experiment_version_conflict(self) -> None:
        with patch("minibench.api.routes.update_experiment", new_callable=AsyncMock) as mock:
            mock.side_effect = ValueError("Version conflict: expected 1, got 2")
            with _client() as client:
                resp = client.post(
                    "/api/experiments/exp-001/revisions",
                    json={"expected_version": 1, "name": "New Name"},
                    headers=REVIEWER_HEADERS,
                )
        assert resp.status_code == 409

    def test_update_experiment_not_found(self) -> None:
        with patch("minibench.api.routes.update_experiment", new_callable=AsyncMock) as mock:
            mock.side_effect = ValueError("Experiment 'exp-001' not found")
            with _client() as client:
                resp = client.post(
                    "/api/experiments/exp-001/revisions",
                    json={"expected_version": 1},
                    headers=REVIEWER_HEADERS,
                )
        assert resp.status_code == 404
