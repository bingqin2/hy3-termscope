from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from termscope.contracts import (
    AgentConfig,
    DeterministicFacts,
    EvaluationResult,
    Finding,
    FirstError,
    HumanLabel,
    HumanReview,
    JudgeResult,
    MergedVerdict,
    ReplayResult,
    TaskRef,
)

NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


def test_taskref_rejects_unknown_difficulty():
    with pytest.raises(ValidationError):
        TaskRef(name="x", git_commit="abc", difficulty="extreme", category="misc")


def test_models_are_frozen():
    ref = TaskRef(name="x", git_commit="abc", difficulty="easy", category="misc")
    with pytest.raises(ValidationError):
        ref.name = "y"


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        AgentConfig(config_id="c", agent="oracle", bogus=1)


def test_finding_requires_valid_taxonomy():
    with pytest.raises(ValidationError):
        Finding(step_id=1, error_type="vibes", severity="high", rationale="r")
    f = Finding(step_id=1, error_type="reasoning", severity="high", rationale="r")
    assert f.recovered is False


def test_first_error_unlocatable_allows_null_step():
    fe = FirstError(location="unlocatable")
    assert fe.step_id is None


def test_evaluation_result_round_trip():
    ev = EvaluationResult(
        bundle_id="b" * 64,
        evaluator_version="v1",
        created_at=NOW,
        deterministic=DeterministicFacts(),
        replay=ReplayResult(feasible=False, localization="unlocatable"),
        judge=JudgeResult(status="unavailable"),
        merged=MergedVerdict(
            process=None,
            first_error=FirstError(location="unlocatable"),
        ),
    )
    again = EvaluationResult.model_validate_json(ev.model_dump_json())
    assert again == ev


def test_human_review_versioning_fields():
    hr = HumanReview(
        bundle_id="b" * 64,
        reviewer="owner",
        version=1,
        blinded=True,
        created_at=NOW,
        label=HumanLabel(process="invalid", first_error=FirstError(location="located", step_id=4)),
    )
    assert hr.blinded and hr.version == 1
