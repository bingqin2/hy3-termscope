"""Pydantic contracts for TermScope run bundles, evaluations, and human reviews.

Mirrors docs/EVALUATOR_SPEC.md. All stored records are immutable (frozen models);
corrections happen by appending new versions, never by editing stored ones.

The trajectory step shape is pinned against the format Harbor's terminus-2 agent
actually emits (Day 1 live trial); oracle trials carry no trajectory.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Difficulty = Literal["easy", "medium", "hard"]
Outcome = Literal["resolved", "unresolved", "inconclusive"]
ProcessVerdict = Literal["valid", "partial", "invalid"]
ErrorType = Literal[
    "task_interpretation",
    "investigation",
    "reasoning",
    "action_execution",
    "implementation",
    "verification",
    "process_integrity",
]
Severity = Literal["low", "medium", "high", "critical"]
Localization = Literal["located", "none", "unlocatable"]
Provenance = Literal["official", "evaluator", "human", "second_rater", "mixed"]
CheckStatus = Literal["passed", "failed", "skipped", "other"]
JudgeStatus = Literal["ok", "unavailable", "context_limit"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TaskRef(_Frozen):
    """Identity of a benchmark task, pinned to the dataset revision."""

    name: str
    dataset: str = "terminal-bench@2.0"
    git_commit: str
    difficulty: Difficulty
    category: str


class AgentConfig(_Frozen):
    """The generating configuration of a run (never shown to the judge)."""

    config_id: str  # e.g. "hy3-terminus-2"
    agent: str  # harbor agent name: oracle | terminus-2 | mini-swe-agent
    model: str | None = None  # None for oracle


class FileRecord(_Frozen):
    """One file inside a bundle, content-addressed."""

    path: str  # relative to the trial dir
    sha256: str
    bytes: int


class CheckResult(_Frozen):
    """One verifier check parsed from ctrf.json."""

    name: str
    status: CheckStatus
    message: str | None = None


class VerifierRecord(_Frozen):
    """The official verifier's output for a trial."""

    reward: float | None  # None when the verifier produced no reward
    checks: tuple[CheckResult, ...] = ()


class TrajectoryStep(_Frozen):
    """One agent step. Field names follow the pinned Harbor trajectory format."""

    step_id: int  # 1-based, sequential
    source: str  # e.g. "agent" | "user" | "system"
    content: str  # message / reasoning text as emitted
    command: str | None = None  # executed terminal input, if any
    observation: str | None = None  # terminal output attributed to this step
    extra: dict[str, str] = Field(default_factory=dict)


class TokenUsage(_Frozen):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class RunBundle(_Frozen):
    """An immutable, content-hashed record of one trial.

    `bundle_id` is the sha256 of the canonical JSON of every other field;
    `verify_bundle_id` in the importer recomputes and compares it.
    """

    bundle_id: str
    created_at: datetime
    task: TaskRef
    config: AgentConfig
    outcome: Outcome
    reward: float | None
    verifier: VerifierRecord
    trajectory: tuple[TrajectoryStep, ...] | None  # None for oracle trials
    files: tuple[FileRecord, ...]
    token_usage: TokenUsage | None = None
    trial_name: str  # harbor trial dir name, e.g. "fix-git__YSb8a5a"
    exception: str | None = None  # harbor-recorded trial exception, if any


class Finding(_Frozen):
    """One process finding, always anchored to a step."""

    step_id: int
    error_type: ErrorType
    severity: Severity
    rationale: str
    recovered: bool = False


class FirstError(_Frozen):
    location: Localization
    step_id: int | None = None


class DeterministicFacts(_Frozen):
    """Zero-model-call facts extracted from the bundle (EVALUATOR_SPEC §3)."""

    destructive_command_steps: tuple[int, ...] = ()
    failed_streaks: tuple[tuple[int, int], ...] = ()  # (start_step, length)
    repeated_command_loops: tuple[tuple[int, int], ...] = ()  # (step, repeat count)
    unverified_success_claim: bool = False
    protected_read_steps: tuple[int, ...] = ()  # recorded facts, never violations
    protected_write_steps: tuple[int, ...] = ()  # recognized write patterns, exit 0
    transient_edit_steps: tuple[int, ...] = ()  # modify-then-revert warnings
    hard_process_failure: bool = False
    notes: tuple[str, ...] = ()


class PrefixCheck(_Frozen):
    """Replay lane: outcome of one probe after commands 1..k.

    ``direct``: do the task's checks already pass at prefix k?
    ``reachability``: after prefix k, does completing the task from that state
    (oracle solution, then checks) still succeed? — the spec's "reachable
    outcome".
    """

    prefix_k: int
    reward: float | None
    passed: bool | None
    probe: Literal["direct", "reachability"] = "reachability"
    seconds: float | None = None


class ReplayResult(_Frozen):
    """Prefix-replay causal localization (EVALUATOR_SPEC §3, flagship)."""

    feasible: bool
    localization: Localization
    first_error_step: int | None = None
    matrix: tuple[PrefixCheck, ...] = ()
    notes: tuple[str, ...] = ()


class JudgeResult(_Frozen):
    """Semantic lane output (EVALUATOR_SPEC §4). Honest failure states included."""

    status: JudgeStatus
    verdict: ProcessVerdict | None = None
    findings: tuple[Finding, ...] = ()
    first_error: FirstError | None = None
    rubric_version: str = "rubric-v1"
    prompt_version: str = "prompt-v1"
    judge_model: str = "hy3"
    retried: bool = False


class MergedVerdict(_Frozen):
    """Merge policy output (EVALUATOR_SPEC §5)."""

    process: ProcessVerdict | None  # None when inconclusive
    first_error: FirstError
    judge_earlier_step: int | None = None  # reasoning-level step, recorded alongside
    primary_error_type: ErrorType | None = None
    correct_result_invalid_process: bool | None = None
    flagged_for_human_review: bool = False


class EvaluationResult(_Frozen):
    """One evaluator pass over one bundle. Stored results are never modified."""

    bundle_id: str
    evaluator_version: str  # "v1" | "v2"
    created_at: datetime
    deterministic: DeterministicFacts
    replay: ReplayResult | None  # None when replay was not run for this bundle
    judge: JudgeResult | None  # None when skipped (e.g. inconclusive outcome)
    merged: MergedVerdict


class HumanLabel(_Frozen):
    process: ProcessVerdict | None = None
    first_error: FirstError | None = None
    error_type: ErrorType | None = None


class HumanReview(_Frozen):
    """One append-only human review version for one bundle."""

    bundle_id: str
    reviewer: str
    version: int  # 1-based, append-only
    blinded: bool  # captured before any evaluator output was revealed
    created_at: datetime
    label: HumanLabel
    notes: str = ""
