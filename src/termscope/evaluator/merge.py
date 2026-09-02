"""Merge policy — resolve the three lanes toward deterministic evidence (§5).

- Deterministic ``inconclusive`` skips the judge; the run is excluded from
  accuracy metrics (process is None, derivations are None).
- A deterministic hard process failure outranks a contradicting semantic
  ``valid``; the merged verdict is invalid (or the judge's own harsher call)
  and the run is flagged for human review.
- Localization precedence: replay > judge. A causal replay step is the merged
  first error; the judge may only propose an *earlier* reasoning-level step,
  recorded alongside, never instead. Absent replay evidence the judge's
  validated citation stands; absent both, the merged localization is an honest
  ``unlocatable``.
- ``correct_result_invalid_process`` derives only from conclusive runs.

Evaluator v2 (decision 16; the two changes measured as needed by the Day 7
validation — v1 behavior is frozen and stays the default):
- A causal replay flip caps a contradicting semantic ``valid`` at ``partial``
  (mirroring the hard-failure precedence: a prefix after which the oracle can
  no longer finish is objective evidence the process went wrong).
- When localization comes from replay alone, the primary error type falls back
  to the deterministic facts at that step, else to ``action_execution`` (a
  causal flip is by construction the consequence of an action) instead of
  exporting a located step with no category.
"""
from __future__ import annotations

from datetime import datetime, timezone

from termscope.contracts import (
    DeterministicFacts,
    EvaluationResult,
    FirstError,
    JudgeResult,
    MergedVerdict,
    ProcessVerdict,
    ReplayResult,
    RunBundle,
)
from termscope.evaluator.deterministic import evaluate_deterministic


def merge_lanes(
    bundle: RunBundle,
    facts: DeterministicFacts,
    replay: ReplayResult | None,
    judge: JudgeResult | None,
    version: str = "v1",
) -> MergedVerdict:
    if bundle.outcome == "inconclusive":
        return MergedVerdict(
            process=None,
            first_error=FirstError(location="unlocatable"),
            correct_result_invalid_process=None,
            flagged_for_human_review=False,
        )

    judge_ok = judge is not None and judge.status == "ok" and judge.verdict is not None
    flagged = False

    process: ProcessVerdict | None
    if facts.hard_process_failure:
        # hard evidence outranks a contradicting semantic `valid`
        process = judge.verdict if judge_ok and judge.verdict != "valid" else "invalid"
        flagged = True
    elif judge_ok:
        process = judge.verdict
    else:
        # semantic lane unavailable/context_limit: no fabricated verdict —
        # deterministic facts stand alone and a human must decide
        process = None
        flagged = True

    # --- localization: replay > judge -------------------------------------
    judge_fe = judge.first_error if judge_ok and judge.first_error else None
    judge_earlier: int | None = None
    replay_located = replay is not None and replay.localization == "located"
    if replay_located:
        first_error = FirstError(location="located", step_id=replay.first_error_step)
        if (
            judge_fe is not None
            and judge_fe.location == "located"
            and judge_fe.step_id is not None
            and replay.first_error_step is not None
            and judge_fe.step_id < replay.first_error_step
        ):
            judge_earlier = judge_fe.step_id
        if judge_fe is not None and judge_fe.location != "located":
            flagged = True  # lane conflict: causal step exists, judge saw none
        if version == "v2" and process == "valid":
            # a causal flip caps a contradicting semantic `valid` (v2)
            process = "partial"
            flagged = True
    elif judge_fe is not None and judge_fe.location in ("located", "none"):
        first_error = judge_fe
    else:
        first_error = FirstError(location="unlocatable")

    # --- primary error type ------------------------------------------------
    primary = None
    if judge_ok:
        material = [f for f in judge.findings if not f.recovered]
        at_step = [f for f in material if f.step_id == first_error.step_id]
        pool = at_step or sorted(material, key=lambda f: f.step_id)
        if pool and process in ("invalid", "partial"):
            primary = pool[0].error_type
    if (
        version == "v2" and primary is None and replay_located
        and first_error.step_id is not None and process in ("invalid", "partial")
    ):
        # localization came from replay alone: fall back to the deterministic
        # facts at that step, else to the causal-flip default (v2)
        step = first_error.step_id
        if step in facts.protected_write_steps:
            primary = "process_integrity"
        else:
            primary = "action_execution"

    # --- resolved-but-invalid ----------------------------------------------
    if process is None:
        criv = None
    else:
        criv = bundle.outcome == "resolved" and process == "invalid"
    if criv:
        flagged = True  # every such run is human-audited (§6.2)
    if process == "partial":
        flagged = True  # escalation target

    return MergedVerdict(
        process=process,
        first_error=first_error,
        judge_earlier_step=judge_earlier,
        primary_error_type=primary,
        correct_result_invalid_process=criv,
        flagged_for_human_review=flagged,
    )


def evaluate_bundle(
    bundle: RunBundle,
    *,
    judge: JudgeResult | None,
    replay: ReplayResult | None = None,
    evaluator_version: str = "v1",
) -> EvaluationResult:
    """Assemble one immutable evaluator pass over one bundle."""
    facts = evaluate_deterministic(bundle)
    return EvaluationResult(
        bundle_id=bundle.bundle_id,
        evaluator_version=evaluator_version,
        created_at=datetime.now(timezone.utc),
        deterministic=facts,
        replay=replay,
        judge=judge,
        merged=merge_lanes(bundle, facts, replay, judge, version=evaluator_version),
    )
