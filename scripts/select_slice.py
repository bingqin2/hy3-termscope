"""Seeded stratified slice selection for the campaign (ROADMAP decisions 14-15).

Draws the pre-registered slice from the Day 1 gate-passing pool
(data/environment-checks/day1-task-gate.json).

Frame (frozen here, recorded in the output):
- target 20 tasks (band 16-20, floor 12): easy 3 / medium 11 / hard 6 —
  proportional to the gate-passing pool (4 easy / 16 medium / 7 hard) while
  keeping every tier represented;
- per-category cap 2 inside each tier's draw for category breadth (>= 6
  categories overall required; the cap is relaxed by 1, recorded, only if a
  tier cannot fill its quota under it);
- seeded shuffle per tier (seed 20260902); the full shuffled candidate order
  is recorded so every skip is auditable.
"""
import json
import random
from pathlib import Path

SEED = 20260902
QUOTA = {"easy": 3, "medium": 11, "hard": 6}
PER_CATEGORY_CAP = 2

REPO = Path(__file__).resolve().parent.parent
gate = json.loads((REPO / "data" / "environment-checks" / "day1-task-gate.json").read_text())
passers = [t for t in gate["tasks"] if t["viability"] in ("rosetta", "native")]

rng = random.Random(SEED)
candidate_order: dict[str, list[str]] = {}
picked: list[dict] = []
relaxations: list[str] = []

for tier in ("easy", "medium", "hard"):
    tier_tasks = sorted(t["task"] for t in passers if t["difficulty"] == tier)
    rng.shuffle(tier_tasks)
    candidate_order[tier] = list(tier_tasks)
    by_task = {t["task"]: t for t in passers}
    cap = PER_CATEGORY_CAP
    while True:
        cat_count: dict[str, int] = {}
        chosen: list[dict] = []
        for name in tier_tasks:
            if len(chosen) >= QUOTA[tier]:
                break
            cat = by_task[name]["category"]
            if cat_count.get(cat, 0) >= cap:
                continue
            chosen.append(by_task[name])
            cat_count[cat] = cat_count.get(cat, 0) + 1
        if len(chosen) >= QUOTA[tier] or cap > 5:
            if cap > PER_CATEGORY_CAP:
                relaxations.append(f"{tier}: cap relaxed to {cap}")
            break
        cap += 1
    picked.extend(chosen)

categories = sorted({t["category"] for t in picked})
assert len(picked) == sum(QUOTA.values()), f"slice size {len(picked)}"
assert len(categories) >= 6, f"only {len(categories)} categories"
for tier, want in QUOTA.items():
    got = sum(1 for t in picked if t["difficulty"] == tier)
    assert got == want, f"{tier}: {got} != {want}"

slice_doc = {
    "record": "slice-v1",
    "date": "2026-09-01",
    "dataset": gate["dataset"],
    "git_commit_pin": gate["git_commit_pin"],
    "source_gate_record": "data/environment-checks/day1-task-gate.json",
    "seed": SEED,
    "frame": {
        "target": sum(QUOTA.values()),
        "band": "16-20 (floor 12)",
        "tier_quota": QUOTA,
        "per_category_cap": PER_CATEGORY_CAP,
        "cap_relaxations": relaxations,
        "rationale": (
            "proportional to the gate-passing pool (4 easy / 16 medium / 7 hard); "
            "category cap for breadth; no exclusion by runtime or expected "
            "difficulty of grading — heavy tasks stay eligible"
        ),
    },
    "candidate_order": candidate_order,
    "n_selected": len(picked),
    "categories": categories,
    "tasks": [
        {
            "name": t["task"],
            "difficulty": t["difficulty"],
            "category": t["category"],
            "viability": t["viability"],
        }
        for t in sorted(picked, key=lambda x: (x["difficulty"], x["task"]))
    ],
}
out = REPO / "data" / "slices" / "slice-v1.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(slice_doc, indent=1))
print(f"slice-v1: {len(picked)} tasks, {len(categories)} categories -> {out.relative_to(REPO)}")
for t in slice_doc["tasks"]:
    print(f'  {t["difficulty"]:6s} {t["category"]:26s} {t["name"]}')
