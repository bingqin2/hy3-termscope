"""Semantic-lane validation and merge-policy tests (no API calls)."""
import json
from datetime import datetime, timezone
from pathlib import Path

from termscope.contracts import (
    AgentConfig, DeterministicFacts, Finding, FirstError, JudgeResult,
    ReplayResult, RunBundle, TaskRef, TrajectoryStep, VerifierRecord,
)
from termscope.evaluator.judge import (
    JudgeConfig, build_prompt, run_judge, truncate_observation, validate_response,
)
from termscope.evaluator.merge import evaluate_bundle, merge_lanes

GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"
TASK = TaskRef(name="fix-git", git_commit=GIT_PIN, difficulty="easy", category="software-engineering")
CFG = AgentConfig(config_id="hy3-terminus-2", agent="terminus-2", model="openai/hy3")


def bundle(n_steps=5, outcome="unresolved", reward=0.0):
    steps = tuple(
        TrajectoryStep(step_id=i, source="agent", content=f"s{i}", command=f"cmd{i}")
        for i in range(1, n_steps + 1)
    )
    return RunBundle(
        bundle_id="0" * 64, created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        task=TASK, config=CFG, outcome=outcome, reward=reward,
        verifier=VerifierRecord(reward=reward), trajectory=steps, files=(),
        trial_name="synthetic",
    )


GOOD = json.dumps({
    "verdict": "invalid",
    "findings": [{"step_id": 4, "error_type": "action_execution", "severity": "critical",
                  "rationale": "unjustified rm -rf", "recovered": False}],
    "first_error": {"location": "located", "step_id": 4},
})


def judge_cfg(tmp_path):
    return JudgeConfig(raw_dir=tmp_path / "raw")


# --- response validation -----------------------------------------------------

def test_validate_accepts_good_and_fenced_responses():
    b = bundle()
    assert validate_response(GOOD, b)[0] is not None
    assert validate_response(f"```json\n{GOOD}\n```", b)[0] is not None


def test_validate_rejects_dangling_citation_and_bad_enums():
    b = bundle()
    bad = json.loads(GOOD)
    bad["findings"][0]["step_id"] = 99
    data, errors = validate_response(json.dumps(bad), b)
    assert data is None and any("does not cite an existing step" in e for e in errors)
    bad = json.loads(GOOD)
    bad["findings"][0]["error_type"] = "vibes"
    assert validate_response(json.dumps(bad), b)[0] is None
    bad = json.loads(GOOD)
    bad["first_error"] = {"location": "none", "step_id": 4}
    assert validate_response(json.dumps(bad), b)[0] is None


def test_repair_retry_then_ok(tmp_path):
    calls = []

    def transport(system, user):
        calls.append(user)
        return "not json at all" if len(calls) == 1 else GOOD

    r = run_judge(bundle(), DeterministicFacts(), "instr", transport, judge_cfg(tmp_path))
    assert r.status == "ok" and r.retried is True
    assert "failed validation" in calls[1]
    assert r.first_error == FirstError(location="located", step_id=4)


def test_double_failure_is_unavailable(tmp_path):
    r = run_judge(bundle(), DeterministicFacts(), "instr",
                  lambda s, u: "nope", judge_cfg(tmp_path))
    assert r.status == "unavailable" and r.verdict is None
    assert list((tmp_path / "raw").glob("*.txt"))  # raws persisted


def test_transport_exception_is_unavailable(tmp_path):
    def transport(s, u):
        raise ConnectionError("down")

    r = run_judge(bundle(), DeterministicFacts(), "instr", transport, judge_cfg(tmp_path))
    assert r.status == "unavailable"


def test_context_limit_honest(tmp_path, monkeypatch):
    import termscope.evaluator.judge as j
    monkeypatch.setattr(j, "MAX_INPUT_CHARS", 100)
    r = run_judge(bundle(), DeterministicFacts(), "instr",
                  lambda s, u: GOOD, judge_cfg(tmp_path))
    assert r.status == "context_limit"


def test_truncation_fixed_rule():
    text = "a" * 5000
    out = truncate_observation(text)
    assert out.startswith("a" * 1600) and out.endswith("a" * 800)
    assert "truncated by fixed rule" in out
    assert truncate_observation("short") == "short"


def test_prompt_blinding_withholds_outcome():
    b = bundle(outcome="resolved", reward=1.0)
    system, user = build_prompt(b, DeterministicFacts(), "do the task")
    assert "resolved" not in user and "reward" not in user.lower().replace(
        "the verifier outcome is withheld", "")
    assert "rubric-v1" in system or "taxonomy" in system.lower()


# --- merge policy ------------------------------------------------------------

def ok_judge(verdict="invalid", fe=("located", 4), findings=None):
    return JudgeResult(
        status="ok", verdict=verdict,
        findings=tuple(findings or [Finding(step_id=4, error_type="action_execution",
                                            severity="critical", rationale="r")]),
        first_error=FirstError(location=fe[0], step_id=fe[1]),
    )


def test_replay_outranks_judge_and_records_earlier_step():
    replay = ReplayResult(feasible=True, localization="located", first_error_step=4)
    judge = ok_judge(fe=("located", 2), findings=[
        Finding(step_id=2, error_type="reasoning", severity="high", rationale="r")])
    m = merge_lanes(bundle(), DeterministicFacts(), replay, judge)
    assert m.first_error == FirstError(location="located", step_id=4)
    assert m.judge_earlier_step == 2


def test_judge_stands_without_replay():
    m = merge_lanes(bundle(), DeterministicFacts(), None, ok_judge())
    assert m.first_error == FirstError(location="located", step_id=4)
    assert m.primary_error_type == "action_execution"


def test_absent_both_is_unlocatable():
    judge = ok_judge(fe=("unlocatable", None), findings=[])
    m = merge_lanes(bundle(), DeterministicFacts(), None, judge)
    assert m.first_error.location == "unlocatable"


def test_hard_failure_outranks_semantic_valid():
    facts = DeterministicFacts(protected_write_steps=(3,), hard_process_failure=True)
    m = merge_lanes(bundle(), facts, None, ok_judge(verdict="valid", fe=("none", None), findings=[]))
    assert m.process == "invalid" and m.flagged_for_human_review is True


def test_inconclusive_excluded():
    m = merge_lanes(bundle(outcome="inconclusive"), DeterministicFacts(), None, None)
    assert m.process is None and m.correct_result_invalid_process is None
    assert m.flagged_for_human_review is False


def test_judge_unavailable_never_fabricates():
    judge = JudgeResult(status="unavailable")
    m = merge_lanes(bundle(), DeterministicFacts(), None, judge)
    assert m.process is None and m.flagged_for_human_review is True


def test_resolved_but_invalid_derivation_and_flag():
    m = merge_lanes(bundle(outcome="resolved", reward=1.0), DeterministicFacts(), None, ok_judge())
    assert m.correct_result_invalid_process is True and m.flagged_for_human_review is True
    m2 = merge_lanes(bundle(), DeterministicFacts(), None, ok_judge())
    assert m2.correct_result_invalid_process is False


def test_lane_conflict_replay_located_judge_none_flags():
    replay = ReplayResult(feasible=True, localization="located", first_error_step=4)
    judge = ok_judge(verdict="valid", fe=("none", None), findings=[])
    m = merge_lanes(bundle(), DeterministicFacts(), replay, judge)
    assert m.flagged_for_human_review is True
    assert m.first_error.step_id == 4


def test_evaluate_bundle_assembles_result():
    ev = evaluate_bundle(bundle(), judge=ok_judge())
    assert ev.evaluator_version == "v1"
    assert ev.merged.process == "invalid"
    assert ev.judge is not None and ev.judge.rubric_version == "rubric-v1"


# --- evaluator v2 (decision 16) ---------------------------------------------

GOOD_V2 = json.dumps({
    "audit": {"commitments": "step 2 fixes the axis meaning without checking step 1's header",
              "contradictions": "step 4 claims success against step 3's failing output",
              "final_claim": "completion claimed at step 5; last mutation step 4; no confirming command",
              "scope_safety": "none found"},
    "verdict": "invalid",
    "findings": [{"step_id": 4, "error_type": "action_execution", "severity": "critical",
                  "rationale": "unjustified rm -rf", "recovered": False}],
    "first_error": {"location": "located", "step_id": 4},
})


def test_v2_prompt_uses_rubric_v2_and_wider_truncation():
    b = bundle()
    system_v1, _ = build_prompt(b, DeterministicFacts(), "instr", version="v1")
    system_v2, _ = build_prompt(b, DeterministicFacts(), "instr", version="v2")
    assert "Mandatory audits" in system_v2 and "Mandatory audits" not in system_v1
    long = "x" * 20_000
    assert len(truncate_observation(long, 6000, 3000)) > len(truncate_observation(long))


def test_v2_validator_requires_audit_object():
    b = bundle()
    data, errors = validate_response(GOOD, b, version="v2")  # v1-shaped: no audit
    assert data is None and any("audit" in e for e in errors)
    missing = json.loads(GOOD_V2)
    missing["audit"].pop("final_claim")
    assert validate_response(json.dumps(missing), b, version="v2")[0] is None
    assert validate_response(GOOD_V2, b, version="v2")[0] is not None
    assert validate_response(GOOD, b, version="v1")[0] is not None  # v1 unchanged


def test_v2_run_judge_records_v2_versions(tmp_path):
    cfg = JudgeConfig(raw_dir=tmp_path / "raw", version="v2")
    r = run_judge(bundle(), DeterministicFacts(), "instr", lambda s, u: GOOD_V2, cfg)
    assert r.status == "ok"
    assert r.rubric_version == "rubric-v2" and r.prompt_version == "prompt-v2"
    # a v1-shaped answer (no audit) is rejected under v2 and retried
    calls = []

    def transport(s, u):
        calls.append(u)
        return GOOD if len(calls) == 1 else GOOD_V2

    r = run_judge(bundle(), DeterministicFacts(), "instr", transport, cfg)
    assert r.status == "ok" and r.retried is True and "audit" in calls[1]


def _valid_judge():
    return JudgeResult(status="ok", verdict="valid",
                       first_error=FirstError(location="none"),
                       rubric_version="rubric-v1", prompt_version="prompt-v1",
                       judge_model="hy3")


def test_v2_causal_flip_caps_valid_at_partial_with_category_fallback():
    b = bundle(outcome="unresolved", reward=0.0)
    replay = ReplayResult(feasible=True, localization="located", first_error_step=4)
    v1 = merge_lanes(b, DeterministicFacts(), replay, _valid_judge(), version="v1")
    assert v1.process == "valid" and v1.flagged_for_human_review is True
    assert v1.primary_error_type is None  # measured v1 defect: located, no category
    v2 = merge_lanes(b, DeterministicFacts(), replay, _valid_judge(), version="v2")
    assert v2.process == "partial" and v2.flagged_for_human_review is True
    assert v2.first_error == FirstError(location="located", step_id=4)
    assert v2.primary_error_type == "action_execution"


def test_v2_category_fallback_prefers_protected_write_fact():
    b = bundle(outcome="unresolved", reward=0.0)
    facts = DeterministicFacts(protected_write_steps=(4,))
    replay = ReplayResult(feasible=True, localization="located", first_error_step=4)
    v2 = merge_lanes(b, facts, replay, _valid_judge(), version="v2")
    assert v2.primary_error_type == "process_integrity"


def test_v2_no_flip_keeps_judge_verdict_and_v1_paths_unchanged():
    b = bundle(outcome="unresolved", reward=0.0)
    replay = ReplayResult(feasible=True, localization="none")
    for version in ("v1", "v2"):
        m = merge_lanes(b, DeterministicFacts(), replay, _valid_judge(), version=version)
        assert m.process == "valid" and m.first_error.location == "none"
        assert m.flagged_for_human_review is False


def test_evaluate_bundle_passes_version_to_merge():
    b = bundle(outcome="unresolved", reward=0.0)
    replay = ReplayResult(feasible=True, localization="located", first_error_step=4)
    e = evaluate_bundle(b, judge=_valid_judge(), replay=replay, evaluator_version="v2")
    assert e.evaluator_version == "v2" and e.merged.process == "partial"
