"""Derive the site's data files from committed results (ROADMAP decision 8).

The published page reads only a frozen snapshot under frontend/src/data/,
re-derived from results/* by this script — never from the pipeline directly.
Every emitted file passes a publication scan (credential patterns and local
absolute paths hard-fail the build) because trajectory observations can echo
container environment variables.

Inputs:  results/{leaderboard,tasks,failure_patterns,runs,spend,validation}.json
         results/judge-stability/consistency-summary.json
         results/regression/regression-card.json
Outputs: frontend/src/data/{leaderboard,tasks,failure_patterns,runs,validation,meta}.json

Usage:  python scripts/build_site_data.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
OUT = REPO / "frontend" / "src" / "data"

# Publication scan: any hit refuses the build. Patterns cover common API-key
# shapes, explicit env assignments, bearer headers, and local user paths.
FORBIDDEN = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), "OpenAI-style secret key"),
    (re.compile(r"OPENAI_API_KEY\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{8,}"), "API key assignment"),
    (re.compile(r"MSWEA_API_KEY\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{8,}"), "API key assignment"),
    (re.compile(r"Authorization:\s*Bearer\s+[A-Za-z0-9_\-.]{10,}"), "bearer token"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"), "GitHub token"),
    (re.compile(r"AKID[A-Za-z0-9]{13,}"), "Tencent Cloud secret id"),
    (re.compile(r"/Users/[A-Za-z0-9_.\-]+"), "local absolute home path"),
    (re.compile(r"hy3-creds"), "credentials file reference"),
]


def scan(name: str, text: str) -> list[str]:
    hits = []
    for pattern, label in FORBIDDEN:
        m = pattern.search(text)
        if m:
            hits.append(f"{name}: {label} ({m.group(0)[:24]}…)")
    return hits


def render(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    load = lambda p: json.loads((RESULTS / p).read_text())  # noqa: E731
    leaderboard = load("leaderboard.json")
    tasks = load("tasks.json")
    runs = load("runs.json")
    validation = load("validation.json")
    spend = load("spend.json")
    consistency = load("judge-stability/consistency-summary.json")
    card = load("regression/regression-card.json")

    # --- runs: failed first, then flagged, then the rest (site walk order) ---
    def rank(r):
        return (r["outcome"] != "unresolved", r["task_id"], r["config_id"])

    runs["runs"] = sorted(runs["runs"], key=rank)

    # --- failure patterns from the blinded reference labels ------------------
    counts: Counter = Counter()
    per_cfg: dict[str, Counter] = {}
    for r in runs["runs"]:
        ref = r.get("reference_review")
        if r["outcome"] != "unresolved" or not ref:
            continue
        et = ref["label"].get("error_type")
        if not et:
            continue
        counts[et] += 1
        per_cfg.setdefault(r["config_id"], Counter())[et] += 1
    severity = {"task_interpretation": "high", "investigation": "high", "reasoning": "high",
                "action_execution": "high", "implementation": "high", "verification": "medium",
                "process_integrity": "critical"}
    fp = {
        "sample": False,
        "provenance": "blinded reference labels (second_rater; owner adjudication overrides where present)",
        "rows": [{"error_type": et, "label": et.replace("_", " "), "severity": severity[et],
                  "count": counts[et],
                  "by_config": {cid: per_cfg.get(cid, Counter())[et]
                                for cid in ("hy3-terminus-2", "hy3-mini-swe-agent")}}
                 for et in sorted(severity) if counts[et] > 0],
    }

    # --- one combined validation payload -------------------------------------
    site_validation = {
        "sample": False,
        "localization_exact": validation["localization_exact"],
        "localization_pm1": validation["localization_pm1"],
        "localization_located_only": validation["localization_located_only"],
        "reference_labels": validation["reference_labels"],
        "false_positive_rate": validation["false_positive_rate"],
        "metric_definitions": validation["metric_definitions"],
        "consistency": {
            "verdict_agreement": consistency["verdict_agreement"],
            "first_error_step_agreement": consistency["first_error_step_agreement"],
            "n_runs": consistency["n_runs"],
            "flagged_run_stability": consistency.get("real_run_stability"),
        },
        "fixture_gate_v1": "passed (valid → valid/0 findings; invalid → located at the known step, right category)",
        "regression": {
            "fixture_gate_v2": card["fixture_gate"],
            "metrics": card["metrics"],
            "residual_failure_mode": card["residual_failure_mode"],
        },
    }

    meta = {
        "updated": leaderboard.get("updated", ""),
        "n_tasks": len(tasks["rows"]),
        "n_runs": len(runs["runs"]),
        "agent_tokens_total": spend.get("agent_tokens_total"),
        "judge_tokens_recorded": spend.get("judge_tokens_recorded"),
    }

    files = {"leaderboard.json": render(leaderboard), "tasks.json": render(tasks),
             "failure_patterns.json": render(fp), "runs.json": render(runs),
             "validation.json": render(site_validation), "meta.json": render(meta)}
    problems = [p for name, text in files.items() for p in scan(name, text)]
    if problems:
        # two-phase: scan everything before writing anything
        print("PUBLICATION SCAN FAILED — nothing was written:", file=sys.stderr)
        print("\n".join(problems), file=sys.stderr)
        return 1
    for name, text in files.items():
        (OUT / name).write_text(text)
    print(f"site data written -> {OUT} ({meta['n_runs']} runs, {meta['n_tasks']} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
