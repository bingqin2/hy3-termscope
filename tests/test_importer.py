import json
from pathlib import Path

import pytest

from termscope.contracts import AgentConfig, TaskRef
from termscope.importer import derive_outcome, import_trial, verify_bundle, write_bundle

TASK = TaskRef(name="fix-git", git_commit="69671fba", difficulty="easy", category="software-engineering")
ORACLE = AgentConfig(config_id="oracle", agent="oracle")


def make_trial(tmp_path: Path, reward: str = "1.0", exception: dict | None = None) -> Path:
    trial = tmp_path / "fix-git__abc1234"
    (trial / "verifier").mkdir(parents=True)
    (trial / "agent").mkdir()
    result = {"id": "t-1", "exception_info": exception}
    (trial / "result.json").write_text(json.dumps(result))
    (trial / "verifier" / "reward.txt").write_text(reward)
    (trial / "verifier" / "ctrf.json").write_text(
        json.dumps(
            {
                "results": {
                    "tests": [
                        {"name": "test_repo_clean", "status": "passed"},
                        {"name": "test_log_intact", "status": "failed", "message": "boom"},
                    ]
                }
            }
        )
    )
    (trial / "trial.log").write_text("log line\n")
    return trial


def test_import_basic(tmp_path):
    bundle = import_trial(make_trial(tmp_path), task=TASK, config=ORACLE)
    assert bundle.outcome == "resolved"
    assert bundle.reward == 1.0
    assert bundle.trajectory is None
    assert {c.name: c.status for c in bundle.verifier.checks} == {
        "test_repo_clean": "passed",
        "test_log_intact": "failed",
    }
    assert len(bundle.files) == 4
    assert verify_bundle(bundle)


def test_hash_is_content_sensitive(tmp_path):
    a = import_trial(make_trial(tmp_path), task=TASK, config=ORACLE)
    tampered = a.model_copy(update={"reward": 0.0})
    assert not verify_bundle(tampered)


def test_hash_stable_for_same_content(tmp_path):
    from datetime import datetime, timezone

    t = datetime(2026, 9, 1, tzinfo=timezone.utc)
    trial = make_trial(tmp_path)
    a = import_trial(trial, task=TASK, config=ORACLE, created_at=t)
    b = import_trial(trial, task=TASK, config=ORACLE, created_at=t)
    assert a.bundle_id == b.bundle_id


def test_outcome_policy():
    assert derive_outcome(1.0, None) == "resolved"
    assert derive_outcome(0.0, None) == "unresolved"
    assert derive_outcome(None, None) == "inconclusive"
    assert derive_outcome(1.0, "{'kind': 'infra'}") == "inconclusive"


def test_agent_timeout_is_agent_failure_not_inconclusive(tmp_path):
    assert derive_outcome(0.0, '{"exception_type": "AgentTimeoutError"}') == "unresolved"
    assert derive_outcome(1.0, '{"exception_type": "AgentTimeoutError"}') == "resolved"
    bundle = import_trial(
        make_trial(tmp_path, reward="0", exception={"exception_type": "AgentTimeoutError",
                                                     "exception_message": "timed out"}),
        task=TASK, config=ORACLE,
    )
    assert bundle.outcome == "unresolved"
    assert bundle.exception is not None  # still recorded for transparency


def test_context_window_exhaustion_is_agent_failure(tmp_path):
    exc = '{"exception_type": "NonZeroAgentExitCodeError"}'
    assert derive_outcome(0.0, exc, "ContextWindowExceededError") == "unresolved"
    assert derive_outcome(0.0, exc, None) == "inconclusive"  # unexplained crash stays honest
    trial = make_trial(tmp_path, reward="0",
                       exception={"exception_type": "NonZeroAgentExitCodeError"})
    (trial / "agent" / "mini-swe-agent.trajectory.json").write_text(
        json.dumps({"info": {"exit_status": "ContextWindowExceededError"}, "messages": []}))
    bundle = import_trial(trial, task=TASK, config=ORACLE)
    assert bundle.outcome == "unresolved"
    assert "ContextWindowExceededError" in (bundle.exception or "")


def test_resource_kill_is_agent_failure(tmp_path):
    killed = '{"exception_message": "Command failed (exit 137): mini-swe-agent ...", "exception_type": "NonZeroAgentExitCodeError"}'
    assert derive_outcome(0.0, killed) == "unresolved"
    crashed = '{"exception_message": "Command failed (exit 1): mini-swe-agent ...", "exception_type": "NonZeroAgentExitCodeError"}'
    assert derive_outcome(0.0, crashed) == "inconclusive"


def test_exception_is_inconclusive(tmp_path):
    bundle = import_trial(
        make_trial(tmp_path, exception={"type": "EnvironmentBuildError"}),
        task=TASK,
        config=ORACLE,
    )
    assert bundle.outcome == "inconclusive"


ATIF = {
    "schema_version": "ATIF-v1.7",
    "session_id": "s-1",
    "agent": {"name": "terminus-2", "version": "x", "model_name": "openai/hy3"},
    "steps": [
        {
            "step_id": 1,
            "source": "user",
            "message": "Fix the git repository in /app.",
        },
        {
            "step_id": 2,
            "source": "agent",
            "message": "Looking around first.",
            "reasoning_content": "I should inspect the repo state.",
            "tool_calls": [
                {"tool_call_id": "c1", "function_name": "bash", "arguments": {"command": "git status"}}
            ],
            "observation": {
                "results": [{"source_call_id": "c1", "content": "on branch main\n"}]
            },
            "metrics": {"prompt_tokens": 900, "completion_tokens": 80},
        },
    ],
    "final_metrics": {"total_prompt_tokens": 900, "total_completion_tokens": 80},
}


def test_import_atif_trajectory(tmp_path):
    trial = make_trial(tmp_path)
    (trial / "agent" / "trajectory.json").write_text(json.dumps(ATIF))
    bundle = import_trial(trial, task=TASK, config=ORACLE)
    assert bundle.trajectory is not None and len(bundle.trajectory) == 2
    s2 = bundle.trajectory[1]
    assert s2.source == "agent"
    assert s2.command == "git status"
    assert s2.observation == "on branch main\n"
    assert s2.extra["reasoning_content"] == "I should inspect the repo state."
    assert bundle.token_usage is not None
    assert bundle.token_usage.input_tokens == 900
    assert bundle.token_usage.total_tokens == 980
    assert verify_bundle(bundle)


def test_import_prefers_atif_over_native_sibling(tmp_path):
    """mini-swe-agent emits its native trajectory next to the ATIF one."""
    trial = make_trial(tmp_path)
    (trial / "agent" / "mini-swe-agent.trajectory.json").write_text(
        json.dumps({"trajectory_format": "mini-swe-agent-1", "messages": [{"role": "user", "content": "x"}]})
    )
    (trial / "agent" / "trajectory.json").write_text(json.dumps(ATIF))
    bundle = import_trial(trial, task=TASK, config=ORACLE)
    assert bundle.trajectory is not None and len(bundle.trajectory) == 2
    assert bundle.token_usage is not None and bundle.token_usage.input_tokens == 900


def test_write_bundle_refuses_conflicting_overwrite(tmp_path):
    from datetime import datetime, timezone

    t = datetime(2026, 9, 1, tzinfo=timezone.utc)
    bundle = import_trial(make_trial(tmp_path), task=TASK, config=ORACLE, created_at=t)
    out = tmp_path / "bundles"
    path = write_bundle(bundle, out)
    assert path.exists()
    assert write_bundle(bundle, out) == path  # idempotent for identical content
    conflicting = bundle.model_copy(update={"trial_name": "other"})
    with pytest.raises(FileExistsError):
        write_bundle(conflicting, out)
