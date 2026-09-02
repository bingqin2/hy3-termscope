"""Export the site/report tables from stored evaluation artifacts.

Every table is re-derived from results/per_run/* (+ human reviews when
present) so the numbers are reproducible from the repo alone. Output is
byte-stable: sorted keys, fixed ordering, and an `updated` stamp derived from
the campaign manifest rather than the wall clock.

Provenance (EVALUATOR_SPEC §6): outcomes are `official` (verifier); process
labels are `human` where an adjudication exists, else `evaluator`; empty
denominators export null, never a fabricated zero.

Usage:
    python scripts/export_results.py [--out DIR]   (default: results/)
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from termscope.contracts import (
    DeterministicFacts, EvaluationResult, JudgeResult, ReplayResult, RunBundle,
)
from termscope.evaluator.merge import merge_lanes

REPO = Path(__file__).resolve().parent.parent
PER_RUN = REPO / "results" / "per_run"
REVIEWS = REPO / "results" / "human_reviews"
WORK = Path.home() / "termscope-work"
MANIFEST = WORK / "campaign-manifest.json"

prereg = json.loads((REPO / "data" / "slices" / "preregistration.json").read_text())
CONFIGS = [c["config_id"] for c in prereg["configs"]]
LABELS = {"hy3-terminus-2": "Hy3 × terminus-2", "hy3-mini-swe-agent": "Hy3 × mini-swe-agent"}
SEVERITY = {
    "task_interpretation": "high", "investigation": "high", "reasoning": "high",
    "action_execution": "high", "implementation": "high", "verification": "medium",
    "process_integrity": "critical",
}
OBS_CHARS = 1500


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def load_run(d: Path) -> dict | None:
    if not (d / "bundle.json").exists():
        return None
    bundle = RunBundle.model_validate_json((d / "bundle.json").read_text())
    facts = DeterministicFacts.model_validate_json((d / "deterministic.json").read_text()) \
        if (d / "deterministic.json").exists() else None
    judge = JudgeResult.model_validate_json((d / "judge.json").read_text()) \
        if (d / "judge.json").exists() else None
    replay = ReplayResult.model_validate_json((d / "replay.json").read_text()) \
        if (d / "replay.json").exists() else None
    evaluation = EvaluationResult.model_validate_json((d / "evaluation.json").read_text()) \
        if (d / "evaluation.json").exists() else None
    if evaluation is not None:
        merged, provisional = evaluation.merged, False
    elif facts is not None:
        merged, provisional = merge_lanes(bundle, facts, replay, judge), True
    else:
        merged, provisional = None, True
    review = latest_blinded_review(d.name)
    return {"key": d.name, "bundle": bundle, "facts": facts, "judge": judge, "replay": replay,
            "merged": merged, "provisional": provisional, "review": review}


def latest_blinded_review(key: str) -> dict | None:
    rd = REVIEWS / key
    if not rd.exists():
        return None
    versions = sorted(rd.glob("review-v*.json"))
    if not versions:
        return None
    return json.loads(versions[-1].read_text())


def process_label(run: dict) -> tuple[str | None, str]:
    """Adjudicated process label with provenance: human overrides evaluator."""
    review = run["review"]
    if review and review.get("label", {}).get("process"):
        return review["label"]["process"], "human"
    if run["merged"] is not None:
        return run["merged"].process, "evaluator"
    return None, "evaluator"


def main(argv: list[str] | None = None) -> int:
    global PER_RUN, REVIEWS, MANIFEST
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "results"))
    ap.add_argument("--per-run", default=str(PER_RUN))
    ap.add_argument("--reviews", default=str(REVIEWS))
    ap.add_argument("--manifest", default=str(MANIFEST))
    args = ap.parse_args(argv)
    PER_RUN, REVIEWS, MANIFEST = Path(args.per_run), Path(args.reviews), Path(args.manifest)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"runs": {}}
    updated = max((r.get("finished") or "" for r in manifest["runs"].values()), default="")[:19]

    # a superseded attempt (decision-12 infrastructure re-run) stays on record
    # but is excluded from every table; its re-run carries the campaign result
    superseded = {k for k, v in manifest["runs"].items() if v.get("superseded_by")}
    runs = [r for r in (load_run(d) for d in sorted(PER_RUN.iterdir()) if d.is_dir())
            if r and r["key"] not in superseded]
    slice_tasks = json.loads((REPO / "data" / "slices" / "slice-v1.json").read_text())["tasks"]

    # --- leaderboard ---------------------------------------------------------
    rows = []
    for cid in CONFIGS:
        mine = [r for r in runs if r["bundle"].config.config_id == cid]
        conclusive = [r for r in mine if r["bundle"].outcome != "inconclusive"]
        resolved = [r for r in conclusive if r["bundle"].outcome == "resolved"]
        labeled = [(r, *process_label(r)) for r in conclusive]
        pred = [r for r in conclusive if r["merged"] is not None and r["merged"].process is not None]
        pred_valid = [r for r in pred if r["merged"].process == "valid"]
        adj = [x for x in labeled if x[1] is not None]
        adj_valid = [x for x in adj if x[1] == "valid"]
        rows.append({
            "config_id": cid, "label": LABELS.get(cid, cid),
            "n_runs": len(mine), "n_inconclusive": len(mine) - len(conclusive),
            "resolve_rate": (len(resolved) / len(conclusive)) if conclusive else None,
            "mean_score": (len(resolved) / len(conclusive)) if conclusive else None,
            "process_validity_rate_predicted": (len(pred_valid) / len(pred)) if pred else None,
            "process_validity_rate_adjudicated": (len(adj_valid) / len(adj)) if adj else None,
            "tasks_won": len(resolved),
            "provenance": {"resolve_rate": "official",
                           "process_validity_rate_predicted": "evaluator",
                           "process_validity_rate_adjudicated": "mixed" if any(x[2] == "human" for x in adj) else "evaluator"},
        })
    dump(out / "leaderboard.json", {"sample": False, "updated": updated, "rows": rows})

    # --- tasks ---------------------------------------------------------------
    by_task_cfg = {(r["bundle"].task.name, r["bundle"].config.config_id): r for r in runs}
    task_rows = []
    for t in slice_tasks:
        cells = {}
        for cid in CONFIGS:
            r = by_task_cfg.get((t["name"], cid))
            if r is None:
                cells[cid] = None
                continue
            proc, prov = process_label(r)
            cells[cid] = {"outcome": r["bundle"].outcome, "reward": r["bundle"].reward,
                          "process": proc, "process_provenance": prov,
                          "resolved_but_invalid": (r["merged"].correct_result_invalid_process
                                                   if r["merged"] else None)}
        task_rows.append({"task_id": t["name"], "name": t["name"], "category": t["category"],
                          "difficulty": t["difficulty"], "cells": cells})
    dump(out / "tasks.json", {"sample": False, "rows": task_rows})

    # --- failure patterns ----------------------------------------------------
    counts: Counter = Counter()
    per_cfg: dict[str, Counter] = defaultdict(Counter)
    for r in runs:
        m = r["merged"]
        if m is None or m.process not in ("invalid", "partial") or not m.primary_error_type:
            continue
        counts[m.primary_error_type] += 1
        per_cfg[r["bundle"].config.config_id][m.primary_error_type] += 1
    fp_rows = [{"error_type": et, "label": et.replace("_", " "), "severity": SEVERITY[et],
                "count": counts[et], "by_config": {cid: per_cfg[cid][et] for cid in CONFIGS}}
               for et in sorted(SEVERITY)]
    dump(out / "failure_patterns.json", {"sample": False, "provenance": "evaluator", "rows": fp_rows})

    # --- runs (explorer) -----------------------------------------------------
    run_rows = []
    for r in runs:
        b, m = r["bundle"], r["merged"]
        proc, prov = process_label(r)
        mrun = manifest["runs"].get(r["key"], {})
        primary_finding = None
        if r["judge"] and r["judge"].findings and m and m.first_error.step_id is not None:
            for f in r["judge"].findings:
                if f.step_id == m.first_error.step_id and not f.recovered:
                    primary_finding = f.rationale
                    break
        run_rows.append({
            "run_id": r["key"], "task_id": b.task.name, "config_id": b.config.config_id,
            "difficulty": b.task.difficulty, "category": b.task.category,
            "outcome": b.outcome, "reward": b.reward, "score": b.reward,
            "process": proc, "process_provenance": prov, "provisional": r["provisional"],
            "first_error_step": m.first_error.step_id if m else None,
            "first_error_location": m.first_error.location if m else None,
            "judge_earlier_step": m.judge_earlier_step if m else None,
            "error_types": [m.primary_error_type] if m and m.primary_error_type else [],
            "finding": primary_finding,
            "replay": None if r["replay"] is None else {
                "localization": r["replay"].localization, "step": r["replay"].first_error_step},
            "judge_status": r["judge"].status if r["judge"] else None,
            "checks": [{"name": c.name, "status": c.status} for c in b.verifier.checks],
            "steps": [{"step_id": s.step_id, "source": s.source,
                       "content": (s.content or "")[:OBS_CHARS],
                       "command": s.command,
                       "observation": (s.observation or "")[:OBS_CHARS]}
                      for s in (b.trajectory or ())],
            "token_usage": None if b.token_usage is None else {
                "input": b.token_usage.input_tokens, "output": b.token_usage.output_tokens,
                "total": b.token_usage.total_tokens},
            "wall_sec": mrun.get("wall_sec"),
            "human_review": None if r["review"] is None else {
                "version": r["review"]["version"], "blinded": r["review"]["blinded"],
                "label": r["review"]["label"]},
        })
    dump(out / "runs.json", {"sample": False, "updated": updated, "runs": run_rows})

    # --- spend ---------------------------------------------------------------
    spend = {"updated": updated, "per_config": {}, "runs": []}
    for cid in CONFIGS:
        mine = [r for r in runs if r["bundle"].config.config_id == cid]
        tok = [r["bundle"].token_usage.total_tokens for r in mine
               if r["bundle"].token_usage and r["bundle"].token_usage.total_tokens]
        wall = [manifest["runs"].get(r["key"], {}).get("wall_sec") or 0 for r in mine]
        spend["per_config"][cid] = {"n_runs": len(mine), "agent_tokens": sum(tok),
                                    "agent_tokens_mean": (sum(tok) / len(tok)) if tok else None,
                                    "wall_sec": sum(wall)}
    judge_tokens = 0
    for r in runs:
        ju = PER_RUN / r["key"] / "judge-usage.json"
        jt = 0
        if ju.exists():
            for u in json.loads(ju.read_text()):
                jt += (u.get("prompt_tokens") or 0) + (u.get("completion_tokens") or 0)
        judge_tokens += jt
        spend["runs"].append({"run_id": r["key"],
                              "agent_tokens": r["bundle"].token_usage.total_tokens if r["bundle"].token_usage else None,
                              "judge_tokens": jt or None,
                              "wall_sec": manifest["runs"].get(r["key"], {}).get("wall_sec")})
    spend["agent_tokens_total"] = sum(v["agent_tokens"] for v in spend["per_config"].values())
    spend["judge_tokens_recorded"] = judge_tokens
    dump(out / "spend.json", spend)

    # --- validation (denominators filled by the Day 7/8 protocol) -------------
    day5 = REPO / "data" / "environment-checks" / "day5-judge-gate.json"
    stability = json.loads(day5.read_text())["stability_summary"] if day5.exists() else None
    labeled_failed = [r for r in runs if r["review"] and r["review"].get("blinded")
                      and r["bundle"].outcome == "unresolved"]
    exact = pm1 = 0
    for r in labeled_failed:
        hs = (r["review"]["label"].get("first_error") or {}).get("step_id")
        ms = r["merged"].first_error.step_id if r["merged"] else None
        if hs is not None and ms is not None:
            exact += hs == ms
            pm1 += abs(hs - ms) <= 1
    flagged_resolved = [r for r in runs if r["merged"] and r["merged"].correct_result_invalid_process]
    audited = [r for r in flagged_resolved if r["review"]]
    false_alarms = [r for r in audited if r["review"]["label"].get("process") == "valid"]
    validation = {
        "sample": False,
        "localization_exact": {"num": exact if labeled_failed else None, "den": len(labeled_failed) or None},
        "localization_pm1": {"num": pm1 if labeled_failed else None, "den": len(labeled_failed) or None},
        "false_positive_rate": {"num": len(false_alarms) if audited else None, "den": len(audited) or None},
        "discriminative": None,
        "stability": stability,
        "regression": None,
        "provenance": {"localization": "mixed (replay/judge vs human)", "false_positive_rate": "human"},
    }
    dump(out / "validation.json", validation)

    print(f"exported {len(runs)} runs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
