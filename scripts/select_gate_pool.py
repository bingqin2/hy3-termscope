"""Seeded selection of the Day 1 oracle-gate candidate pool for terminal-bench@2.0.

Rules (recorded in the output):
- every `easy` task is included (the tier is scarce: 4 tasks);
- remaining slots filled by seeded round-robin over categories (sorted order),
  each category's tasks shuffled with the fixed seed, per-category cap 2;
- at most 3 "heavy" tasks (agent timeout >= 3600s), so the gate's wall-clock
  stays bounded while Rosetta viability of heavy builds is still probed;
- target pool size 28;
- if fewer than 7 hard tasks land in the pool, seeded hard swaps top it up.
"""
import json
import random
from pathlib import Path

SEED = 20260901
TARGET = 28
PER_CATEGORY_CAP = 2
HEAVY_CAP = 3
HARD_MIN = 7

WORK = Path.home() / "termscope-work"
rows = json.loads((WORK / "tb2-inventory.json").read_text())
by_name = {r["name"]: r for r in rows}

heavy = lambda r: (r["agent_timeout_sec"] or 0) >= 3600
rng = random.Random(SEED)

pool = [r["name"] for r in rows if r["difficulty"] == "easy"]

cats = {}
for r in rows:
    if r["name"] not in pool:
        cats.setdefault(r["category"], []).append(r["name"])
for c in cats:
    cats[c].sort()
    rng.shuffle(cats[c])

taken_per_cat = {}
heavy_count = sum(1 for n in pool if heavy(by_name[n]))
rounds = 0
while len(pool) < TARGET and rounds < 10:
    rounds += 1
    for c in sorted(cats):
        if len(pool) >= TARGET:
            break
        if taken_per_cat.get(c, 0) >= PER_CATEGORY_CAP:
            continue
        while cats[c]:
            cand = cats[c].pop(0)
            r = by_name[cand]
            if heavy(r) and heavy_count >= HEAVY_CAP:
                continue
            pool.append(cand)
            taken_per_cat[c] = taken_per_cat.get(c, 0) + 1
            heavy_count += heavy(r)
            break

hard_in_pool = [n for n in pool if by_name[n]["difficulty"] == "hard"]
if len(hard_in_pool) < HARD_MIN:
    hard_rest = sorted(
        n for n, r in by_name.items()
        if r["difficulty"] == "hard" and n not in pool and not heavy(r)
    )
    rng.shuffle(hard_rest)
    med_in_pool = [n for n in pool if by_name[n]["difficulty"] == "medium"]
    rng.shuffle(med_in_pool)
    while len(hard_in_pool) < HARD_MIN and hard_rest and med_in_pool:
        out, inn = med_in_pool.pop(0), hard_rest.pop(0)
        pool[pool.index(out)] = inn
        hard_in_pool.append(inn)

pool_rows = [by_name[n] for n in sorted(pool)]
summary = {
    "seed": SEED,
    "rules": __doc__.strip(),
    "pool_size": len(pool),
    "by_difficulty": {
        d: sum(1 for r in pool_rows if r["difficulty"] == d)
        for d in ("easy", "medium", "hard")
    },
    "categories": sorted({r["category"] for r in pool_rows}),
    "heavy_tasks": [r["name"] for r in pool_rows if heavy(r)],
    "tasks": [
        {
            "name": r["name"],
            "difficulty": r["difficulty"],
            "category": r["category"],
            "agent_timeout_sec": r["agent_timeout_sec"],
        }
        for r in pool_rows
    ],
}
(WORK / "gate-pool.json").write_text(json.dumps(summary, indent=1))
print(json.dumps({k: summary[k] for k in ("pool_size", "by_difficulty", "heavy_tasks")}, indent=1))
print("categories:", len(summary["categories"]))
print("\n".join(f'{r["difficulty"]:6s} {r["category"]:26s} {r["name"]}' for r in pool_rows))
