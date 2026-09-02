"""Day 4 exit measurement: replay the invalid fixture (expect located step 8)
and one real trial (the Day 1 live solve), recording runtimes per probe.

Writes data/environment-checks/day4-replay-measurement.json.
Local Docker only; zero model calls.
"""
import json
import sys
import time
from pathlib import Path

from termscope.contracts import AgentConfig, TaskRef
from termscope.evaluator.replay import DockerReplayEnv, localize
from termscope.importer import import_trial

REPO = Path(__file__).resolve().parent.parent
TB2_SRC = Path.home() / "termscope-work" / "tb2-src"
GIT_PIN = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"

FIXGIT = TaskRef(name="fix-git", git_commit=GIT_PIN, difficulty="easy",
                 category="software-engineering")
HY3_T2 = AgentConfig(config_id="hy3-terminus-2", agent="terminus-2", model="openai/hy3")


def run_one(label: str, trial_dir: Path) -> dict:
    bundle = import_trial(trial_dir, task=FIXGIT, config=HY3_T2)
    env = DockerReplayEnv(
        image="alexgshaw/fix-git:20251031",
        workdir="/app/personal-site",
        tests_dir=TB2_SRC / "fix-git" / "tests",
        solution_dir=TB2_SRC / "fix-git" / "solution",
        log=lambda s: print(f"[{label}] {s}", flush=True),
    )
    started = time.monotonic()
    result = localize(bundle, env)
    wall = round(time.monotonic() - started, 1)
    print(f"[{label}] localization={result.localization} "
          f"step={result.first_error_step} wall={wall}s", flush=True)
    return {
        "trial": trial_dir.name,
        "localization": result.localization,
        "first_error_step": result.first_error_step,
        "feasible": result.feasible,
        "n_probes": len(result.matrix),
        "probe_seconds": [p.seconds for p in result.matrix],
        "wall_seconds": wall,
        "notes": list(result.notes),
        "matrix": [
            {"k": p.prefix_k, "passed": p.passed, "probe": p.probe, "seconds": p.seconds}
            for p in result.matrix
        ],
    }


def main() -> int:
    record = {
        "record": "day4-replay-measurement",
        "date": "2026-09-01",
        "task": "fix-git (image alexgshaw/fix-git:20251031, workdir /app/personal-site)",
        "method": (
            "fresh container per probe; trajectory command prefix 1..k executed in one "
            "non-interactive shell session (PAGER=cat, TERM=dumb); reachability probe = "
            "oracle solution then checks; first permanent reachability flip = causal "
            "first error; bisection with a repeat probe at the flip"
        ),
        "invalid_fixture": run_one(
            "invalid-fixture", REPO / "data" / "fixtures" / "invalid-known-first-error" / "trial"
        ),
        "real_trial": run_one(
            "real-trial", next(Path.home().glob("termscope-work/jobs/day1-live-terminus-fix-git/fix-git__*"))
        ),
    }
    expected = json.loads(
        (REPO / "data" / "fixtures" / "invalid-known-first-error" / "expected-oracle.json").read_text()
    )["first_error"]["step_id"]
    record["exit_condition"] = {
        "expected_fixture_step": expected,
        "replay_pinpointed": record["invalid_fixture"]["first_error_step"] == expected
        and record["invalid_fixture"]["localization"] == "located",
    }
    out = REPO / "data" / "environment-checks" / "day4-replay-measurement.json"
    out.write_text(json.dumps(record, indent=1))
    print(f"written {out}", flush=True)
    return 0 if record["exit_condition"]["replay_pinpointed"] else 1


if __name__ == "__main__":
    sys.exit(main())
