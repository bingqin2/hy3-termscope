"""Import a Harbor trial directory into an immutable, content-hashed RunBundle.

Layout consumed (harbor 0.22.0, verified on the Day 1 smoke trial):

    <job>/<task>__<suffix>/
        config.json      trial config (task ref, agent, model)
        result.json      trial result (reward, exception, timing)
        trial.log
        agent/...        agent artifacts (trajectory for LLM agents)
        verifier/reward.txt
        verifier/ctrf.json
        artifacts/manifest.json

The bundle id is the sha256 of the bundle's canonical JSON with the
`bundle_id` field blanked; `verify_bundle` recomputes and compares.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from termscope.contracts import (
    AgentConfig,
    CheckResult,
    CheckStatus,
    FileRecord,
    Outcome,
    RunBundle,
    TaskRef,
    TokenUsage,
    TrajectoryStep,
    VerifierRecord,
)

_BLANK = "0" * 64


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_hash(bundle: RunBundle) -> str:
    payload = bundle.model_copy(update={"bundle_id": _BLANK}).model_dump_json()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_ctrf(path: Path) -> tuple[CheckResult, ...]:
    if not path.exists():
        return ()
    data = json.loads(path.read_text())
    tests = (data.get("results") or {}).get("tests") or []
    out = []
    for t in tests:
        raw = str(t.get("status", "other"))
        status: CheckStatus = raw if raw in ("passed", "failed", "skipped") else "other"
        out.append(
            CheckResult(
                name=str(t.get("name", "?")),
                status=status,
                message=t.get("message"),
            )
        )
    return tuple(out)


def _parse_reward(trial_dir: Path, result: dict) -> float | None:
    reward_txt = trial_dir / "verifier" / "reward.txt"
    if reward_txt.exists():
        text = reward_txt.read_text().strip()
        if text:
            return float(text)
    verifier = result.get("verifier_result") or {}
    rewards = verifier.get("rewards") or {}
    for key in ("reward", "score"):
        if isinstance(rewards.get(key), (int, float)):
            return float(rewards[key])
    return None


AGENT_FAILURE_EXCEPTIONS = ("AgentTimeoutError",)
# agent-side exit statuses (from the agent's native trajectory) that mean the
# model/scaffold pair hit its own limits rather than the environment breaking
MODEL_LIMIT_EXIT_STATUSES = ("ContextWindowExceededError",)
# exit 137 = SIGKILL: the agent process was killed inside the task's official
# resource limits (cgroup memory cap) — a budget violated by the agent's own
# actions, graded like a timeout
RESOURCE_KILL_MARKERS = ("(exit 137)",)


def derive_outcome(
    reward: float | None, exception: str | None, agent_exit_status: str | None = None
) -> Outcome:
    """Outcome policy (EVALUATOR_SPEC §3): infrastructure failure is inconclusive.

    An agent exhausting its official time budget, or the model's context
    window, is the agent failing — not the environment: harbor still runs the
    verifier, and the reward decides.
    """
    agent_failure = exception is not None and (
        any(name in exception for name in AGENT_FAILURE_EXCEPTIONS)
        or (
            "NonZeroAgentExitCodeError" in exception
            and (
                (agent_exit_status is not None
                 and any(s in agent_exit_status for s in MODEL_LIMIT_EXIT_STATUSES))
                or any(m in exception for m in RESOURCE_KILL_MARKERS)
            )
        )
    )
    if exception is not None and not agent_failure:
        return "inconclusive"
    if reward is None:
        return "inconclusive"
    return "resolved" if reward > 0 else "unresolved"


def agent_exit_status(trial_dir: Path) -> str | None:
    """The agent's own exit status from a native trajectory file, if recorded."""
    for path in sorted(trial_dir.glob("agent/*.trajectory.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        info = data.get("info") if isinstance(data, dict) else None
        if isinstance(info, dict) and info.get("exit_status"):
            return str(info["exit_status"])
    return None


def _text(value) -> str:
    """Flatten an ATIF string-or-ContentPart-list message to text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for p in value:
            if isinstance(p, dict):
                parts.append(str(p.get("text") or p.get("content") or ""))
            else:
                parts.append(str(p))
        return "\n".join(x for x in parts if x)
    return str(value)


def load_trajectory(trial_dir: Path) -> tuple[TrajectoryStep, ...] | None:
    """Load the agent trajectory if one exists (None for oracle trials).

    Pinned format: ATIF (harbor 0.22.0 emits schema_version <= ATIF-v1.7).
    Step: {step_id, source: system|user|agent, message, reasoning_content,
    tool_calls: [{tool_call_id, function_name, arguments}],
    observation: {results: [{source_call_id, content}]}, metrics}.
    """
    data = _load_atif(trial_dir)
    if data is None:
        return None
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        return None
    steps = []
    for i, s in enumerate(raw_steps, start=1):
        if not isinstance(s, dict):
            continue
        # terminus-2 issues terminal input as arguments.keystrokes (possibly
        # several tool calls per step); other agents use arguments.command.
        parts = []
        for tc in s.get("tool_calls") or []:
            args = tc.get("arguments") if isinstance(tc, dict) else None
            if not isinstance(args, dict):
                continue
            for key in ("command", "keystrokes"):
                if isinstance(args.get(key), str):
                    parts.append(args[key].rstrip("\n"))
                    break
        command = "\n".join(p for p in parts if p) or None
        observation = None
        obs = s.get("observation")
        if isinstance(obs, dict):
            texts = [_text(r.get("content")) for r in obs.get("results") or [] if isinstance(r, dict)]
            observation = "\n".join(t for t in texts if t) or None
        extra: dict[str, str] = {}
        if s.get("reasoning_content"):
            extra["reasoning_content"] = str(s["reasoning_content"])
        steps.append(
            TrajectoryStep(
                step_id=int(s.get("step_id") or i),
                source=str(s.get("source") or "agent"),
                content=_text(s.get("message")),
                command=command,
                observation=observation,
                extra=extra,
            )
        )
    return tuple(steps)


def _load_atif(trial_dir: Path) -> dict | None:
    """Locate the ATIF trajectory among agent files.

    Some agents (mini-swe-agent) also emit their native trajectory next to the
    ATIF one; only a document with an ATIF ``schema_version`` and a ``steps``
    list qualifies. ``agent/trajectory.json`` is preferred when present.
    """
    candidates = sorted(
        trial_dir.glob("agent/*trajectory*.json"),
        key=lambda p: (p.name != "trajectory.json", p.name),
    )
    for path in candidates:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(data, dict)
            and str(data.get("schema_version", "")).startswith("ATIF")
            and isinstance(data.get("steps"), list)
        ):
            return data
    return None


def _token_usage(result: dict, trial_dir: Path) -> TokenUsage | None:
    """Prefer the ATIF trajectory's final_metrics; fall back to agent_result."""
    data = _load_atif(trial_dir)
    if data is not None:
        fm = data.get("final_metrics")
        if isinstance(fm, dict) and any(
            fm.get(k) for k in ("total_prompt_tokens", "total_completion_tokens")
        ):
            inp = fm.get("total_prompt_tokens")
            out = fm.get("total_completion_tokens")
            total = (inp or 0) + (out or 0) if (inp or out) else None
            return TokenUsage(input_tokens=inp, output_tokens=out, total_tokens=total)
    ar = result.get("agent_result") or {}
    usage = ar.get("usage") or ar.get("token_usage") or {}
    if not isinstance(usage, dict) or not usage:
        return None
    return TokenUsage(
        input_tokens=usage.get("input_tokens") or usage.get("prompt_tokens"),
        output_tokens=usage.get("output_tokens") or usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
    )


def import_trial(
    trial_dir: Path,
    *,
    task: TaskRef,
    config: AgentConfig,
    created_at: datetime | None = None,
) -> RunBundle:
    trial_dir = Path(trial_dir)
    result = json.loads((trial_dir / "result.json").read_text())

    files = tuple(
        FileRecord(
            path=str(p.relative_to(trial_dir)),
            sha256=_sha256_file(p),
            bytes=p.stat().st_size,
        )
        for p in sorted(trial_dir.rglob("*"))
        if p.is_file()
    )

    exception = None
    exit_status = agent_exit_status(trial_dir)
    if result.get("exception_info"):
        info = dict(result["exception_info"])
        if exit_status:
            info["agent_exit_status"] = exit_status
        exception = json.dumps(info, sort_keys=True)

    reward = _parse_reward(trial_dir, result)
    bundle = RunBundle(
        bundle_id=_BLANK,
        created_at=created_at or datetime.now(timezone.utc),
        task=task,
        config=config,
        outcome=derive_outcome(reward, exception, exit_status),
        reward=reward,
        verifier=VerifierRecord(
            reward=reward, checks=_parse_ctrf(trial_dir / "verifier" / "ctrf.json")
        ),
        trajectory=load_trajectory(trial_dir),
        files=files,
        token_usage=_token_usage(result, trial_dir),
        trial_name=trial_dir.name,
        exception=exception,
    )
    return bundle.model_copy(update={"bundle_id": _canonical_hash(bundle)})


def verify_bundle(bundle: RunBundle) -> bool:
    """Recompute the content hash; True iff the stored id matches."""
    return bundle.bundle_id == _canonical_hash(bundle)


def write_bundle(bundle: RunBundle, out_dir: Path) -> Path:
    """Persist as <out_dir>/<bundle_id>.json (refuses to overwrite)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{bundle.bundle_id}.json"
    if path.exists():
        existing = RunBundle.model_validate_json(path.read_text())
        if existing == bundle:
            return path
        raise FileExistsError(f"bundle collision at {path}")
    path.write_text(bundle.model_dump_json(indent=1))
    return path
