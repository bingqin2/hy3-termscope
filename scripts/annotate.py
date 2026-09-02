"""Blinded annotation CLI (ROADMAP decision 17, EVALUATOR_SPEC §6).

Labels are captured BEFORE any evaluator output is revealed:
- `list` / `show` never print evaluator verdicts, findings, or replay steps;
- `label` records a timestamped HumanReview as an append-only version under the
  reviewer's own directory; a label is `blinded=True` only if no `reveal` for
  that run precedes it (the reveal marker is per run, so a reveal by anyone
  ends blinding for every later label on that run — the conservative rule);
- `reveal` prints the evaluator's verdict for a run and requires the explicit
  `--show-verdict` flag; every later label for that run is non-blinded and
  excluded from validation metrics by construction.

Reviewers are identified by name (`--reviewer`, default `owner`). The human owner
and an independent model rater are distinct reviewers; `results/reviews/RATERS.json`
documents each one (kind, inputs, blinding). `--attach FILE` stores the rater's raw
output JSON next to the review it produced.

Files: results/reviews/<run>/<reviewer>/review-vN.json (+ review-vN.attachment.json)
       results/reviews/<run>/reveal.json

Usage:
    python scripts/annotate.py list [--all]
    python scripts/annotate.py show <run_id> [--full]
    python scripts/annotate.py label <run_id> --process valid|partial|invalid \
        --first-error <step|none|unlocatable> [--error-type <category>] [--notes TEXT] \
        [--reviewer NAME] [--attach FILE]
    python scripts/annotate.py reveal <run_id> --show-verdict
    python scripts/annotate.py status [--reviewer NAME]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from termscope.contracts import FirstError, HumanLabel, HumanReview, RunBundle

REPO = Path(__file__).resolve().parent.parent
PER_RUN = REPO / "results" / "per_run"
REVIEWS = REPO / "results" / "reviews"
DEFAULT_REVIEWER = "owner"
OBS_CHARS = 1200


def bundle_for(run_id: str) -> RunBundle:
    p = PER_RUN / run_id / "bundle.json"
    if not p.exists():
        sys.exit(f"no bundle for {run_id}")
    return RunBundle.model_validate_json(p.read_text())


def reviewers_for(run_id: str) -> list[str]:
    d = REVIEWS / run_id
    if not d.exists():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def reviews_for(run_id: str, reviewer: str) -> list[Path]:
    """Review versions in numeric order; attachments are not versions."""
    paths = [p for p in (REVIEWS / run_id / reviewer).glob("review-v*.json")
             if not p.name.endswith(".attachment.json")]
    return sorted(paths, key=lambda p: int(p.stem.rsplit("-v", 1)[1]))


def revealed(run_id: str) -> bool:
    return (REVIEWS / run_id / "reveal.json").exists()


def cmd_list(args) -> None:
    rows = []
    for d in sorted(PER_RUN.iterdir()):
        if not (d / "bundle.json").exists():
            continue
        b = bundle_for(d.name)
        if b.outcome == "inconclusive":
            continue
        if not args.all and b.outcome != "unresolved":
            continue
        labels = ", ".join(f"{r}:{len(reviews_for(d.name, r))}" for r in reviewers_for(d.name)) or "-"
        rows.append((d.name, b.outcome, labels, "REVEALED" if revealed(d.name) else "blind"))
    print(f"{'run_id':46s} {'outcome':11s} {'labels':28s} state")
    for r in rows:
        print(f"{r[0]:46s} {r[1]:11s} {r[2]:28s} {r[3]}")
    print(f"{len(rows)} runs ({'all conclusive' if args.all else 'failed only'})")


def cmd_show(args) -> None:
    b = bundle_for(args.run_id)
    instr = Path.home() / "termscope-work" / "tb2-src" / b.task.name / "instruction.md"
    print(f"# {args.run_id}  task={b.task.name} ({b.task.difficulty}, {b.task.category})  "
          f"outcome={b.outcome}")
    if instr.exists():
        print("\n## Task instruction\n" + instr.read_text().strip())
    print("\n## Trajectory (no evaluator output shown)")
    for s in b.trajectory or ():
        print(f"\n### Step {s.step_id} ({s.source})")
        if s.content:
            print("message:", s.content if args.full else s.content[:OBS_CHARS])
        if s.command:
            print("command:\n" + s.command)
        if s.observation:
            obs = s.observation if args.full else s.observation[:OBS_CHARS]
            print("observation:\n" + obs + ("" if args.full or len(s.observation) <= OBS_CHARS
                                            else f"\n[... {len(s.observation) - OBS_CHARS} more chars; --full]"))


def cmd_label(args) -> None:
    b = bundle_for(args.run_id)
    step_ids = {s.step_id for s in b.trajectory or ()}
    fe = args.first_error
    if fe in ("none", "unlocatable"):
        first_error = FirstError(location=fe)
    else:
        try:
            step = int(fe)
        except ValueError:
            sys.exit("--first-error must be a step id, 'none', or 'unlocatable'")
        if step not in step_ids:
            sys.exit(f"step {step} does not exist in this trajectory ({min(step_ids)}..{max(step_ids)})")
        first_error = FirstError(location="located", step_id=step)
    if args.process != "valid" and first_error.location == "located" and not args.error_type:
        sys.exit("--error-type is required when a first error is located")
    if args.process == "valid" and first_error.location != "none":
        sys.exit("a valid process has first-error 'none'")
    reviewer = args.reviewer
    existing = reviews_for(args.run_id, reviewer)
    version = len(existing) + 1
    review = HumanReview(
        bundle_id=b.bundle_id, reviewer=reviewer, version=version,
        blinded=not revealed(args.run_id), created_at=datetime.now(timezone.utc),
        label=HumanLabel(process=args.process, first_error=first_error,
                         error_type=args.error_type),
        notes=args.notes or "",
    )
    out = REVIEWS / args.run_id / reviewer
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"review-v{version}.json"
    path.write_text(review.model_dump_json(indent=1))
    if args.attach:
        src = Path(args.attach)
        if not src.exists():
            sys.exit(f"attachment not found: {src}")
        shutil.copyfile(src, out / f"review-v{version}.attachment.json")
    print(f"recorded {path.relative_to(REPO)} (reviewer {reviewer}, version {version}, "
          f"{'BLINDED' if review.blinded else 'non-blinded: evaluator output was revealed earlier'})")


def cmd_reveal(args) -> None:
    if not args.show_verdict:
        sys.exit("verdicts are suppressed by default; pass --show-verdict explicitly "
                 "(this marks all later labels for the run as non-blinded)")
    d = PER_RUN / args.run_id
    b = bundle_for(args.run_id)
    out = REVIEWS / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "reveal.json"
    if not marker.exists():
        before = {r: len(reviews_for(args.run_id, r)) for r in reviewers_for(args.run_id)}
        marker.write_text(json.dumps({"revealed_at": datetime.now(timezone.utc).isoformat(),
                                      "labels_before_reveal": before}, indent=1))
    print(f"# evaluator output for {args.run_id} (outcome={b.outcome})")
    for name in ("deterministic.json", "replay.json", "judge.json", "evaluation.json"):
        p = d / name
        if p.exists():
            print(f"\n## {name}\n" + p.read_text())


def cmd_status(args) -> None:
    total = labeled = blinded = 0
    for d in sorted(PER_RUN.iterdir()):
        if not (d / "bundle.json").exists():
            continue
        b = bundle_for(d.name)
        if b.outcome != "unresolved":
            continue
        total += 1
        rs = reviews_for(d.name, args.reviewer)
        if rs:
            labeled += 1
            first = json.loads(rs[0].read_text())
            blinded += bool(first.get("blinded"))
    print(f"reviewer {args.reviewer}: failed runs: {total}; labeled: {labeled}; "
          f"with a blinded initial label: {blinded}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show"); p.add_argument("run_id"); p.add_argument("--full", action="store_true"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("label"); p.add_argument("run_id")
    p.add_argument("--process", required=True, choices=["valid", "partial", "invalid"])
    p.add_argument("--first-error", required=True)
    p.add_argument("--error-type", choices=["task_interpretation", "investigation", "reasoning",
                                            "action_execution", "implementation", "verification",
                                            "process_integrity"])
    p.add_argument("--notes"); p.add_argument("--reviewer", default=DEFAULT_REVIEWER)
    p.add_argument("--attach", help="raw rater output JSON to store next to the review")
    p.set_defaults(fn=cmd_label)
    p = sub.add_parser("reveal"); p.add_argument("run_id"); p.add_argument("--show-verdict", action="store_true"); p.set_defaults(fn=cmd_reveal)
    p = sub.add_parser("status"); p.add_argument("--reviewer", default=DEFAULT_REVIEWER); p.set_defaults(fn=cmd_status)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
