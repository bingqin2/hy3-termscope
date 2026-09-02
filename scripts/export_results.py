"""Export the site/report tables from stored evaluation artifacts.

Every table is re-derived from results/per_run/* (+ reviews when present) so
the numbers are reproducible from the repo alone. Output is byte-stable:
sorted keys, fixed ordering, and an `updated` stamp derived from the campaign
manifest rather than the wall clock.

Provenance (EVALUATOR_SPEC §6): outcomes are `official` (verifier). Process
labels come from reviews (results/reviews/<run>/<reviewer>/review-vN.json,
reviewers documented in results/reviews/RATERS.json): the owner's latest label
(a blinded label, or an adjudication after reveal) overrides with provenance
`human`; else the independent model rater's blinded label with provenance
`second_rater`; else the evaluator's merged verdict. Validation metrics use
blinded labels only — the owner's when present, otherwise the model rater's —
and report how many of each. Empty denominators export null, never a
fabricated zero.

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
REVIEWS = REPO / "results" / "reviews"
HUMAN_REVIEWER = "owner"
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
    reviews = load_reviews(d.name)
    review, review_prov = reference_review(reviews)
    return {"key": d.name, "bundle": bundle, "facts": facts, "judge": judge, "replay": replay,
            "merged": merged, "provisional": provisional, "reviews": reviews,
            "review": review, "review_provenance": review_prov}


def load_reviews(key: str) -> dict[str, dict]:
    """Per reviewer: the latest review version and the latest *blinded* version."""
    rd = REVIEWS / key
    out: dict[str, dict] = {}
    if not rd.exists():
        return out
    for sub in sorted(p for p in rd.iterdir() if p.is_dir()):
        paths = [p for p in sub.glob("review-v*.json") if not p.name.endswith(".attachment.json")]
        versions = [json.loads(p.read_text())
                    for p in sorted(paths, key=lambda p: int(p.stem.rsplit("-v", 1)[1]))]
        if versions:
            blinded = [v for v in versions if v.get("blinded")]
            out[sub.name] = {"latest": versions[-1], "latest_blinded": blinded[-1] if blinded else None}
    return out


def reference_review(reviews: dict[str, dict]) -> tuple[dict | None, str | None]:
    """Blinded reference label for validation metrics: the owner's blinded label when
    present, else the independent model rater's. Non-blinded labels never qualify."""
    if reviews.get(HUMAN_REVIEWER, {}).get("latest_blinded"):
        return reviews[HUMAN_REVIEWER]["latest_blinded"], "human"
    for name in sorted(reviews):
        if name != HUMAN_REVIEWER and reviews[name].get("latest_blinded"):
            return reviews[name]["latest_blinded"], "second_rater"
    return None, None


def process_label(run: dict) -> tuple[str | None, str]:
    """Adjudicated process label with provenance: the owner's latest label (blinded, or an
    adjudication after reveal) overrides; else the rater's blinded label; else evaluator."""
    human = run["reviews"].get(HUMAN_REVIEWER, {}).get("latest")
    if human and human.get("label", {}).get("process"):
        return human["label"]["process"], "human"
    if run["review"] and run["review"].get("label", {}).get("process"):
        return run["review"]["label"]["process"], run["review_provenance"]
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
                           "process_validity_rate_adjudicated": "mixed" if any(x[2] != "evaluator" for x in adj) else "evaluator"},
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
            "reference_review": None if r["review"] is None else {
                "reviewer": r["review"]["reviewer"], "provenance": r["review_provenance"],
                "version": r["review"]["version"], "blinded": r["review"]["blinded"],
                "label": r["review"]["label"], "notes": r["review"].get("notes", "")},
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
    labeled_failed = [r for r in runs if r["review"] is not None
                      and r["bundle"].outcome == "unresolved"]
    exact = pm1 = loc_num = loc_den = 0
    for r in labeled_failed:
        fe = r["review"]["label"].get("first_error") or {}
        hs, hloc = fe.get("step_id"), fe.get("location")
        ms = r["merged"].first_error.step_id if r["merged"] else None
        mloc = r["merged"].first_error.location if r["merged"] else None
        if hs is not None and ms is not None:
            exact += hs == ms
            pm1 += abs(hs - ms) <= 1
        elif hloc == mloc == "none":
            # both sides assert "no first error": agreement under both tolerances
            exact += 1
            pm1 += 1
        if hloc == "located":
            loc_den += 1
            loc_num += ms is not None and hs == ms
    label_prov = Counter(r["review_provenance"] for r in labeled_failed)
    flagged_resolved = [r for r in runs if r["merged"] and r["merged"].correct_result_invalid_process]
    audited = [r for r in flagged_resolved
               if r["reviews"].get(HUMAN_REVIEWER, {}).get("latest")]
    false_alarms = [r for r in audited
                    if r["reviews"][HUMAN_REVIEWER]["latest"]["label"].get("process") == "valid"]
    validation = {
        "sample": False,
        "localization_exact": {"num": exact if labeled_failed else None, "den": len(labeled_failed) or None},
        "localization_pm1": {"num": pm1 if labeled_failed else None, "den": len(labeled_failed) or None},
        "localization_located_only": {"num": loc_num if loc_den else None, "den": loc_den or None},
        "metric_definitions": {
            "localization_exact": "reference vs merged first error over all labeled failed runs; agreement = same step, or both sides 'none'",
            "localization_located_only": "exact step match restricted to runs whose reference label locates a step"},
        "reference_labels": {"human": label_prov.get("human", 0),
                             "second_rater": label_prov.get("second_rater", 0)} if labeled_failed else None,
        "false_positive_rate": {"num": len(false_alarms) if audited else None, "den": len(audited) or None},
        "discriminative": None,
        "stability": stability,
        "regression": None,
        "provenance": {"localization": "mixed (replay/judge vs blinded reference labels; see reference_labels)",
                       "false_positive_rate": "human"},
    }
    dump(out / "validation.json", validation)

    print(f"exported {len(runs)} runs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
