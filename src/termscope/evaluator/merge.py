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
    if replay is not None and replay.localization == "located":
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
        merged=merge_lanes(bundle, facts, replay, judge),
    )
