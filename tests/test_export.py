"""Exporter tests: leaderboard math, provenance, honest nulls, byte-stability."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from termscope.contracts import (
    AgentConfig, DeterministicFacts, Finding, FirstError, HumanLabel, HumanReview,
    JudgeResult, RunBundle, TaskRef, TrajectoryStep, VerifierRecord,
)

REPO = Path(__file__).resolve().parent.parent
GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_results", REPO / "scripts" / "export_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_bundle(task: str, cfg: str, outcome: str, reward: float, n_steps: int = 3) -> RunBundle:
    steps = tuple(TrajectoryStep(step_id=i, source="agent", content=f"m{i}", command=f"c{i}")
                  for i in range(1, n_steps + 1))
    return RunBundle(
        bundle_id=f"{abs(hash((task, cfg))):064x}"[:64].ljust(64, "0"),
        created_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
        task=TaskRef(name=task, git_commit=GIT_PIN, difficulty="easy", category="software-engineering"),
        config=AgentConfig(config_id=cfg, agent="terminus-2", model="openai/hy3"),
        outcome=outcome, reward=reward, verifier=VerifierRecord(reward=reward),
        trajectory=steps, files=(), trial_name=f"{task}__x",
    )


def write_run(per_run: Path, bundle: RunBundle, judge: JudgeResult | None) -> str:
    key = f"{bundle.config.config_id}__{bundle.task.name}"
    d = per_run / key
    d.mkdir(parents=True)
    (d / "bundle.json").write_text(bundle.model_dump_json())
    (d / "deterministic.json").write_text(DeterministicFacts().model_dump_json())
    if judge is not None:
        (d / "judge.json").write_text(judge.model_dump_json())
    return key


def test_export_tables(tmp_path):
    per_run, reviews, out = tmp_path / "per_run", tmp_path / "reviews", tmp_path / "out"
    valid_judge = JudgeResult(status="ok", verdict="valid", first_error=FirstError(location="none"))
    invalid_judge = JudgeResult(
        status="ok", verdict="invalid",
        findings=(Finding(step_id=2, error_type="reasoning", severity="high", rationale="wrong"),),
        first_error=FirstError(location="located", step_id=2),
    )
    write_run(per_run, make_bundle("fix-git", "hy3-terminus-2", "resolved", 1.0), valid_judge)
    k2 = write_run(per_run, make_bundle("cobol-modernization", "hy3-terminus-2", "unresolved", 0.0), invalid_judge)
    write_run(per_run, make_bundle("fix-git", "hy3-mini-swe-agent", "inconclusive", None), None)
    # a blinded human label that disagrees with the evaluator on the failed run
    b2 = RunBundle.model_validate_json((per_run / k2 / "bundle.json").read_text())
    (reviews / k2).mkdir(parents=True)
    (reviews / k2 / "review-v1.json").write_text(HumanReview(
        bundle_id=b2.bundle_id, reviewer="owner", version=1, blinded=True,
        created_at=datetime(2026, 9, 3, tzinfo=timezone.utc),
        label=HumanLabel(process="partial", first_error=FirstError(location="located", step_id=3),
                         error_type="reasoning"),
    ).model_dump_json())
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"runs": {k2: {"finished": "2026-09-02T10:00:00+00:00", "wall_sec": 12.5}}}))

    exporter = load_exporter()
    argv = ["--out", str(out), "--per-run", str(per_run), "--reviews", str(reviews),
            "--manifest", str(manifest)]
    assert exporter.main(argv) == 0
    first = {p.name: p.read_bytes() for p in out.iterdir()}
    assert exporter.main(argv) == 0
    assert {p.name: p.read_bytes() for p in out.iterdir()} == first  # byte-stable

    lb = {r["config_id"]: r for r in json.loads((out / "leaderboard.json").read_text())["rows"]}
    t2 = lb["hy3-terminus-2"]
    assert t2["n_runs"] == 2 and t2["resolve_rate"] == 0.5
    assert t2["process_validity_rate_predicted"] == 0.5  # valid + invalid
    assert t2["process_validity_rate_adjudicated"] == 0.5  # human 'partial' replaces 'invalid'
    assert t2["provenance"]["process_validity_rate_adjudicated"] == "mixed"
    msa = lb["hy3-mini-swe-agent"]
    assert msa["n_inconclusive"] == 1 and msa["resolve_rate"] is None  # honest null

    runs = {r["run_id"]: r for r in json.loads((out / "runs.json").read_text())["runs"]}
    assert runs[k2]["process"] == "partial" and runs[k2]["process_provenance"] == "human"
    assert runs[k2]["first_error_step"] == 2  # evaluator localization, replay absent
    assert runs[k2]["wall_sec"] == 12.5

    val = json.loads((out / "validation.json").read_text())
    assert val["localization_exact"] == {"num": 0, "den": 1}
    assert val["localization_pm1"] == {"num": 1, "den": 1}
    assert val["false_positive_rate"] == {"num": None, "den": None}  # nothing flagged-resolved

    fp = {r["error_type"]: r for r in json.loads((out / "failure_patterns.json").read_text())["rows"]}
    assert fp["reasoning"]["count"] == 1 and fp["process_integrity"]["count"] == 0
