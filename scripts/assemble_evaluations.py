"""Assemble the immutable evaluator-v1 EvaluationResult for every campaign run.

Reads results/per_run/<key>/{bundle,deterministic,judge,replay}.json and
writes results/per_run/<key>/evaluation.json once. Existing evaluation files
are never overwritten (stored evaluations are immutable; a later evaluator
revision writes evaluation-v2.json via the regression card, never this file).

Run after the replay lane has covered the failed/flagged runs so the merged
localization can apply replay > judge precedence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from termscope.contracts import JudgeResult, ReplayResult, RunBundle
from termscope.evaluator.merge import evaluate_bundle

REPO = Path(__file__).resolve().parent.parent
PER_RUN = REPO / "results" / "per_run"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    ap.add_argument("--show-verdict", action="store_true")
    args = ap.parse_args()
    name = "evaluation.json" if args.version == "v1" else f"evaluation-{args.version}.json"

    counts = {"assembled": 0, "existing": 0, "missing_lanes": 0, "with_replay": 0}
    for d in sorted(PER_RUN.iterdir()):
        if not (d / "bundle.json").exists() or not (d / "deterministic.json").exists():
            counts["missing_lanes"] += 1
            continue
        if (d / name).exists():
            counts["existing"] += 1
            continue
        bundle = RunBundle.model_validate_json((d / "bundle.json").read_text())
        judge = JudgeResult.model_validate_json((d / "judge.json").read_text()) \
            if (d / "judge.json").exists() else None
        replay = ReplayResult.model_validate_json((d / "replay.json").read_text()) \
            if (d / "replay.json").exists() else None
        if bundle.outcome != "inconclusive" and judge is None:
            counts["missing_lanes"] += 1
            continue
        ev = evaluate_bundle(bundle, judge=judge, replay=replay, evaluator_version=args.version)
        (d / name).write_text(ev.model_dump_json(indent=1))
        counts["assembled"] += 1
        counts["with_replay"] += replay is not None
        line = f"assembled {d.name}"
        if args.show_verdict:
            line += f" process={ev.merged.process} first_error={ev.merged.first_error}"
        print(line)
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
