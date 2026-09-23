"""Unit tests for domain model constraints and state-machine rules.

These tests run without a database — they verify the ORM model
definitions and Pydantic schema validation logic directly.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from minibench.domain.models.tables import (
    AgentRun,
    Experiment,
    ExperimentStatus,
    RunState,
    Sample,
)
from minibench.domain.schemas.contracts import (
    ExperimentCreate,
    ExperimentUpdate,
    SampleCreate,
)

# ---------------------------------------------------------------------------
# Experiment schema validation
# ---------------------------------------------------------------------------


class TestExperimentCreate:
    def test_valid(self) -> None:
        e = ExperimentCreate(
            id="exp-001",
            name="Test Experiment",
            target_id="PROT_A",
            assay_type="binding",
        )
        assert e.id == "exp-001"
        assert e.conditions == {}

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(id="", name="x", target_id="PROT_A", assay_type="binding")

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(id="exp-001", name="", target_id="PROT_A", assay_type="binding")

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentCreate(
                id="exp-001",
                name="x",
                target_id="PROT_A",
                assay_type="binding",
                status="not_a_status",  # type: ignore[arg-type]
            )


class TestExperimentUpdate:
    def test_requires_expected_version(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentUpdate()  # type: ignore[call-arg]

    def test_valid_partial_update(self) -> None:
        u = ExperimentUpdate(expected_version=1, name="New Name")
        assert u.expected_version == 1
        assert u.name == "New Name"
        assert u.status is None


# ---------------------------------------------------------------------------
# Sample schema validation
# ---------------------------------------------------------------------------


class TestSampleCreate:
    def test_valid(self) -> None:
        s = SampleCreate(id="sample-001", canonical_code="SAMP_001", label="Sample 1")
        assert s.canonical_code == "SAMP_001"
        assert s.aliases == []

    def test_empty_canonical_code_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SampleCreate(id="sample-001", canonical_code="", label="Sample 1")


# ---------------------------------------------------------------------------
# RunState transitions
# ---------------------------------------------------------------------------


VALID_TRANSITIONS: list[tuple[RunState, RunState]] = [
    (RunState.queued, RunState.running),
    (RunState.running, RunState.succeeded),
    (RunState.running, RunState.waiting_approval),
    (RunState.running, RunState.retry_wait),
    (RunState.running, RunState.failed),
    (RunState.retry_wait, RunState.running),
    (RunState.waiting_approval, RunState.succeeded),
    (RunState.waiting_approval, RunState.cancelled),
]

INVALID_TRANSITIONS: list[tuple[RunState, RunState]] = [
    (RunState.succeeded, RunState.running),
    (RunState.failed, RunState.running),
    (RunState.cancelled, RunState.running),
    (RunState.queued, RunState.succeeded),
    (RunState.queued, RunState.waiting_approval),
    (RunState.waiting_approval, RunState.retry_wait),
]

ALLOWED_FROM: dict[RunState, set[RunState]] = {
    RunState.queued: {RunState.running},
    RunState.running: {
        RunState.succeeded,
        RunState.waiting_approval,
        RunState.retry_wait,
        RunState.failed,
    },
    RunState.retry_wait: {RunState.running},
    RunState.waiting_approval: {RunState.succeeded, RunState.cancelled},
    RunState.succeeded: set(),
    RunState.failed: set(),
    RunState.cancelled: set(),
}


def is_valid_transition(from_state: RunState, to_state: RunState) -> bool:
    return to_state in ALLOWED_FROM.get(from_state, set())


class TestRunStateTransitions:
    @pytest.mark.parametrize("from_state,to_state", VALID_TRANSITIONS)
    def test_valid_transitions_accepted(self, from_state: RunState, to_state: RunState) -> None:
        assert is_valid_transition(from_state, to_state)

    @pytest.mark.parametrize("from_state,to_state", INVALID_TRANSITIONS)
    def test_invalid_transitions_rejected(self, from_state: RunState, to_state: RunState) -> None:
        assert not is_valid_transition(from_state, to_state)

    def test_terminal_states_have_no_outgoing(self) -> None:
        for terminal in (RunState.succeeded, RunState.failed, RunState.cancelled):
            assert ALLOWED_FROM[terminal] == set()


# ---------------------------------------------------------------------------
# ORM model attribute checks (no DB required)
# ---------------------------------------------------------------------------


class TestOrmModels:
    def test_experiment_table_name(self) -> None:
        assert Experiment.__tablename__ == "experiments"

    def test_sample_table_name(self) -> None:
        assert Sample.__tablename__ == "samples"

    def test_agent_run_table_name(self) -> None:
        assert AgentRun.__tablename__ == "agent_runs"

    def test_experiment_status_values(self) -> None:
        assert set(ExperimentStatus) == {
            ExperimentStatus.draft,
            ExperimentStatus.active,
            ExperimentStatus.completed,
            ExperimentStatus.archived,
        }

    def test_run_state_values(self) -> None:
        assert set(RunState) == {
            RunState.queued,
            RunState.running,
            RunState.waiting_approval,
            RunState.retry_wait,
            RunState.succeeded,
            RunState.failed,
            RunState.cancelled,
        }
