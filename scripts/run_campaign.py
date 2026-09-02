"""Pre-registered campaign runner (ROADMAP decisions 12, 14, 15).

Executes data/slices/preregistration.json exactly: tasks in the recorded order,
per task hy3-terminus-2 then hy3-mini-swe-agent, one harbor job per
(task, config) with identical flags, total concurrency 2 (one lane per
config; the second lane never starts task i before the first lane has started
it). A finished run is final — the manifest makes the runner resumable but it
never re-runs a completed (task, config). The decision-12 infrastructure
exception is applied by hand after review, never automatically.

Usage:
    python scripts/run_campaign.py [--dry-run] [--only-first-task]

Environment: harbor on PATH; credentials file at ~/termscope-work/hy3-creds.env
(loaded by harbor via --env-file; never printed).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORK = Path.home() / "termscope-work"
JOBS = WORK / "jobs" / "campaign"
LOGS = WORK / "campaign-logs"
MANIFEST = WORK / "campaign-manifest.json"
CREDS = WORK / "hy3-creds.env"
HARBOR = Path.home() / ".local" / "bin" / "harbor"

prereg = json.loads((REPO / "data" / "slices" / "preregistration.json").read_text())
TASKS: list[str] = prereg["task_list"]["tasks"]
CONFIGS: list[dict] = prereg["configs"]
inventory = {r["name"]: r for r in json.loads((WORK / "tb2-inventory.json").read_text())}

lock = threading.Lock()
started_index = {c["config_id"]: -1 for c in CONFIGS}


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"runs": {}, "created": datetime.now(timezone.utc).isoformat()}


def save_manifest(m: dict) -> None:
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, indent=1))
    tmp.replace(MANIFEST)


def run_key(task: str, config_id: str) -> str:
    return f"{config_id}__{task}"


def trial_result(job_dir: Path) -> tuple[Path | None, dict | None]:
    trials = sorted(p for p in job_dir.glob("*__*") if p.is_dir())
    if not trials:
        return None, None
    trial = trials[-1]
    result_path = trial / "result.json"
    if not result_path.exists():
        return trial, None
    return trial, json.loads(result_path.read_text())


def harbor_cmd(task: str, cfg: dict, job_name: str) -> list[str]:
    return [
        str(HARBOR), "run",
        "-d", "terminal-bench@2.0",
        "-a", cfg["agent"],
        "-m", cfg["model"],
        "--env-file", str(CREDS),
        "-i", task,
        "-o", str(JOBS),
        "--job-name", job_name,
        "-n", "1", "-q", "-y",
    ]


def execute(task: str, cfg: dict, manifest: dict, dry_run: bool) -> None:
    key = run_key(task, cfg["config_id"])
    job_name = key
    job_dir = JOBS / job_name
    cmd = harbor_cmd(task, cfg, job_name)
    if dry_run:
        print("DRY:", " ".join(cmd), flush=True)
        return
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"{key}.log"
    inv = inventory[task]
    cap = int((inv["agent_timeout_sec"] or 900) + (inv["verifier_timeout_sec"] or 900) + 1800)
    started = datetime.now(timezone.utc)
    with lock:
        manifest["runs"][key] = {
            "task": task, "config_id": cfg["config_id"], "job_name": job_name,
            "started": started.isoformat(), "status": "running",
        }
        save_manifest(manifest)
    print(f"[{started.strftime('%H:%M:%S')}] START {key}", flush=True)
    with open(log_path, "w") as log:
        try:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=cap)
            exit_code = proc.returncode
            status_note = None
        except subprocess.TimeoutExpired:
            exit_code = -1
            status_note = f"runner hard cap {cap}s exceeded (harbor did not return)"
    finished = datetime.now(timezone.utc)
    trial, result = trial_result(job_dir)
    reward = None
    exception = None
    if trial is not None:
        rt = trial / "verifier" / "reward.txt"
        if rt.exists() and rt.read_text().strip():
            reward = float(rt.read_text().strip())
    if result is not None and result.get("exception_info"):
        exception = str(result["exception_info"].get("exception_type") or result["exception_info"])[:200]
    entry = {
        "task": task, "config_id": cfg["config_id"], "job_name": job_name,
        "started": started.isoformat(), "finished": finished.isoformat(),
        "wall_sec": round((finished - started).total_seconds(), 1),
        "exit_code": exit_code, "trial_dir": str(trial) if trial else None,
        "reward": reward, "exception": exception,
        "status": "finished" if result is not None else "no-result",
        "note": status_note,
    }
    with lock:
        manifest["runs"][key] = entry
        save_manifest(manifest)
    print(f"[{finished.strftime('%H:%M:%S')}] DONE  {key} reward={reward} "
          f"exception={exception} wall={entry['wall_sec']}s", flush=True)


def lane(cfg: dict, cfg_index: int, manifest: dict, dry_run: bool, only_first: bool) -> None:
    tasks = TASKS[:1] if only_first else TASKS
    for i, task in enumerate(tasks):
        # the second config never starts task i before the primary has started it
        if cfg_index > 0:
            primary = CONFIGS[0]["config_id"]
            while True:
                with lock:
                    if started_index[primary] >= i:
                        break
                time.sleep(5)
        with lock:
            started_index[cfg["config_id"]] = i
            existing = manifest["runs"].get(run_key(task, cfg["config_id"]))
        if existing and existing.get("status") in ("finished", "no-result"):
            print(f"SKIP {run_key(task, cfg['config_id'])} (already {existing['status']}; single attempt is final)",
                  flush=True)
            continue
        execute(task, cfg, manifest, dry_run)


def rerun(key: str, reason: str, manifest: dict) -> int:
    """Decision-12 infrastructure exception: re-run one (task, config) exactly once.

    The broken attempt stays in the manifest (marked superseded_by); the re-run
    is recorded under `<key>__rerun1` with the reason. A second re-run is refused.
    """
    original = manifest["runs"].get(key)
    if original is None or original.get("status") != "finished":
        print(f"{key}: no finished original attempt to supersede", file=sys.stderr)
        return 1
    if original.get("superseded_by"):
        print(f"{key}: already re-run once ({original['superseded_by']}); refusing a second", file=sys.stderr)
        return 1
    cfg = next(c for c in CONFIGS if c["config_id"] == original["config_id"])
    new_key = f"{key}__rerun1"
    execute_as(original["task"], cfg, manifest, new_key)
    with lock:
        manifest["runs"][key]["superseded_by"] = new_key
        manifest["runs"][new_key]["rerun_of"] = key
        manifest["runs"][new_key]["rerun_reason"] = reason
        save_manifest(manifest)
    return 0


def execute_as(task: str, cfg: dict, manifest: dict, key: str) -> None:
    """Run one harbor job under an explicit manifest key / job name."""
    global run_key
    saved = run_key
    run_key = lambda t, c: key  # noqa: E731 — scoped override for this job
    try:
        execute(task, cfg, manifest, dry_run=False)
    finally:
        run_key = saved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only-first-task", action="store_true")
    ap.add_argument("--rerun", metavar="KEY", help="re-run one superseded run (decision-12 exception)")
    ap.add_argument("--reason", default="", help="evidence for the infrastructure exception")
    args = ap.parse_args()
    if not args.dry_run and not CREDS.exists():
        print(f"missing credentials file {CREDS}", file=sys.stderr)
        return 1
    manifest = load_manifest()
    JOBS.mkdir(parents=True, exist_ok=True)
    if args.rerun:
        if not args.reason:
            print("--reason is required for a re-run", file=sys.stderr)
            return 1
        return rerun(args.rerun, args.reason, manifest)
    threads = [
        threading.Thread(target=lane, args=(cfg, idx, manifest, args.dry_run, args.only_first_task),
                         name=cfg["config_id"], daemon=False)
        for idx, cfg in enumerate(CONFIGS)
    ]
    for t in threads:
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    runs = manifest["runs"]
    done = [r for r in runs.values() if r.get("status") in ("finished", "no-result")]
    print(f"campaign lanes finished: {len(done)}/{len(TASKS) * len(CONFIGS)} runs recorded", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
