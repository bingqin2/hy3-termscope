"""Campaign-level record: official outcomes, token and wall-clock spend.

Reads the runner manifest and the imported bundles; writes
data/environment-checks/day6-campaign-record.json. Contains verifier outcomes
and spend only — never evaluator verdicts (blinding, decision 17).
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from termscope.contracts import RunBundle

REPO = Path(__file__).resolve().parent.parent
WORK = Path.home() / "termscope-work"
MANIFEST = WORK / "campaign-manifest.json"
PER_RUN = REPO / "results" / "per_run"

prereg = json.loads((REPO / "data" / "slices" / "preregistration.json").read_text())
CONFIGS = [c["config_id"] for c in prereg["configs"]]
slice_tasks = {t["name"]: t for t in json.loads((REPO / "data" / "slices" / "slice-v1.json").read_text())["tasks"]}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    runs = {k: v for k, v in manifest["runs"].items() if not v.get("superseded_by")}
    bundles: dict[str, RunBundle] = {}
    for key in runs:
        p = PER_RUN / key / "bundle.json"
        if p.exists():
            bundles[key] = RunBundle.model_validate_json(p.read_text())

    started = min(v["started"] for v in runs.values())
    finished = max(v.get("finished") or v["started"] for v in runs.values())
    wall_total = (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds()

    per_config = {}
    for cid in CONFIGS:
        mine = {k: v for k, v in runs.items() if v["config_id"] == cid}
        outcomes = Counter(bundles[k].outcome for k in mine if k in bundles)
        tokens = [bundles[k].token_usage.total_tokens for k in mine
                  if k in bundles and bundles[k].token_usage and bundles[k].token_usage.total_tokens]
        walls = [v.get("wall_sec") or 0 for v in mine.values()]
        by_diff = {}
        for d in ("easy", "medium", "hard"):
            keys = [k for k in mine if slice_tasks[mine[k]["task"]]["difficulty"] == d and k in bundles]
            by_diff[d] = {"n": len(keys),
                          "resolved": sum(bundles[k].outcome == "resolved" for k in keys)}
        per_config[cid] = {
            "n_runs": len(mine),
            "outcomes": dict(outcomes),
            "resolve_rate_official": (outcomes["resolved"] / (outcomes["resolved"] + outcomes["unresolved"]))
            if (outcomes["resolved"] + outcomes["unresolved"]) else None,
            "by_difficulty": by_diff,
            "agent_tokens": {"total": sum(tokens), "mean": round(sum(tokens) / len(tokens)) if tokens else None,
                             "max": max(tokens) if tokens else None, "n_with_usage": len(tokens)},
            "wall_sec": {"total": round(sum(walls), 1), "mean": round(sum(walls) / len(walls), 1) if walls else None,
                         "max": max(walls) if walls else None},
            "exceptions": [{"run": k, "exception": v["exception"], "outcome_after_policy": bundles[k].outcome if k in bundles else None}
                           for k, v in mine.items() if v.get("exception")],
        }

    judge_tokens = 0
    judge_estimated = 0
    for key in runs:
        ju = PER_RUN / key / "judge-usage.json"
        if ju.exists():
            for u in json.loads(ju.read_text()):
                judge_tokens += (u.get("prompt_tokens") or 0) + (u.get("completion_tokens") or 0)
                judge_estimated += bool(u.get("estimated"))

    record = {
        "record": "day6-campaign-record",
        "preregistration": "data/slices/preregistration.json",
        "runs_total": len(runs),
        "superseded_attempts": [k for k, v in manifest["runs"].items() if v.get("superseded_by")],
        "started": started, "finished": finished,
        "wall_clock_hours": round(wall_total / 3600, 2),
        "concurrency": "2 (one lane per config; second lane never starts a task before the first has started it)",
        "per_config": per_config,
        "agent_tokens_total": sum(v["agent_tokens"]["total"] for v in per_config.values()),
        "judge_tokens_recorded": judge_tokens,
        "judge_usage_entries_estimated": judge_estimated,
        "incidents": "results/campaign-incidents.json",
        "note": "official verifier outcomes and spend only; evaluator verdicts are withheld from this record by design",
    }
    out = REPO / "data" / "environment-checks" / "day6-campaign-record.json"
    out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("runs_total", "wall_clock_hours", "agent_tokens_total", "judge_tokens_recorded")}))
    for cid, v in per_config.items():
        print(f"{cid}: outcomes={v['outcomes']} resolve_rate={v['resolve_rate_official']} "
              f"tokens_mean={v['agent_tokens']['mean']} wall_mean={v['wall_sec']['mean']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
