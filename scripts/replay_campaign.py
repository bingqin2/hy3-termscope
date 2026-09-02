"""Replay lane over the campaign: causal localization for failed/flagged runs.

Selection (EVALUATOR_SPEC §3): every run whose outcome is `unresolved`, plus
resolved runs the deterministic lane flags (hard failure or adverse facts).
One replay per run, sequential (Docker CPU), results immutable:
  results/per_run/<key>/replay.json   ReplayResult
  results/per_run/<key>/replay.log    probe-by-probe log

mini-swe-agent executes every action in a fresh subshell, so its commands are
wrapped in `( ... )` before replay to mirror that isolation; terminus-2 drives
one persistent tmux shell, so its commands replay as-is. Zero model calls.

Run only after the campaign has finished (probes compete for CPU with live
agent runs). Usage: python scripts/replay_campaign.py [--only RUN_ID] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from termscope.contracts import DeterministicFacts, RunBundle
from termscope.evaluator.deterministic import deterministic_assessment
from termscope.evaluator.replay import DockerReplayEnv, localize

REPO = Path(__file__).resolve().parent.parent
PER_RUN = REPO / "results" / "per_run"
WORK = Path.home() / "termscope-work"
SRC = WORK / "tb2-src"
inventory = {r["name"]: r for r in json.loads((WORK / "tb2-inventory.json").read_text())}


def image_workdir(image: str) -> str:
    out = subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Config.WorkingDir}}"],
                         capture_output=True, text=True, timeout=30)
    wd = out.stdout.strip()
    return wd if out.returncode == 0 and wd else "/app"


def wrap_subshells(bundle: RunBundle) -> RunBundle:
    steps = tuple(
        s.model_copy(update={"command": f"( {s.command} )" if s.command else None})
        for s in bundle.trajectory
    )
    return bundle.model_copy(update={"trajectory": steps})


def selected(bundle: RunBundle, facts: DeterministicFacts) -> tuple[bool, str]:
    if bundle.outcome == "unresolved":
        return True, "failed run"
    if bundle.outcome == "resolved":
        stance, _ = deterministic_assessment(bundle, facts)
        if stance in ("hard_invalid", "flagged"):
            return True, f"resolved but deterministically {stance}"
    return False, "not selected"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    summary = []
    for d in sorted(PER_RUN.iterdir()):
        if not (d / "bundle.json").exists() or not (d / "deterministic.json").exists():
            continue
        if args.only and d.name != args.only:
            continue
        bundle = RunBundle.model_validate_json((d / "bundle.json").read_text())
        facts = DeterministicFacts.model_validate_json((d / "deterministic.json").read_text())
        sel, why = selected(bundle, facts)
        if not sel:
            continue
        if (d / "replay.json").exists():
            summary.append((d.name, "existing"))
            continue
        task = bundle.task.name
        inv = inventory[task]
        image = inv["docker_image"]
        if args.dry_run:
            print(f"DRY {d.name}: {why}; image={image}")
            continue

        log_lines: list[str] = []
        env = DockerReplayEnv(
            image=image,
            workdir=image_workdir(image),
            tests_dir=SRC / task / "tests",
            solution_dir=SRC / task / "solution",
            check_timeout_sec=float(inv["verifier_timeout_sec"] or 900),
            prefix_timeout_sec=float(min(inv["agent_timeout_sec"] or 900, 1800)),
            log=lambda s: (log_lines.append(s), print(f"  {s}", flush=True)),
        )
        replay_bundle = bundle
        extra_notes: tuple[str, ...] = (f"selected: {why}",)
        if bundle.config.agent == "mini-swe-agent":
            replay_bundle = wrap_subshells(bundle)
            extra_notes += ("commands wrapped in subshells to mirror mini-swe-agent's per-action isolation",)

        print(f"replay {d.name} ({why}) ...", flush=True)
        t0 = time.monotonic()
        result = localize(replay_bundle, env, probe="reachability")
        elapsed = round(time.monotonic() - t0, 1)
        result = result.model_copy(update={"notes": result.notes + extra_notes + (f"replay wall {elapsed}s",)})
        (d / "replay.json").write_text(result.model_dump_json(indent=1))
        (d / "replay.log").write_text("\n".join(log_lines) + "\n")
        summary.append((d.name, f"{result.localization} probes={len(result.matrix)} {elapsed}s"))
        print(f"  -> {result.localization} ({len(result.matrix)} probes, {elapsed}s)", flush=True)

    for name, status in summary:
        print(f"{name:46s} {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
