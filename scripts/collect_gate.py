"""Collect Day 1 oracle-gate results into a committed-ready environment-check record."""
import json
import subprocess
from pathlib import Path

WORK = Path.home() / "termscope-work"
JOB = WORK / "jobs" / "day1-gate"
pool = json.loads((WORK / "gate-pool.json").read_text())
by_name = {t["name"]: t for t in pool["tasks"]}
inventory = {r["name"]: r for r in json.loads((WORK / "tb2-inventory.json").read_text())}


def image_arch(image: str) -> str:
    try:
        out = subprocess.run(
            ["docker", "image", "inspect", image, "--format", "{{.Os}}/{{.Architecture}}"],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


rows = []
for name, meta in sorted(by_name.items()):
    trial_dirs = sorted(JOB.glob(f"{name}__*"))
    row = {
        "task": name,
        "difficulty": meta["difficulty"],
        "category": meta["category"],
        "docker_image": inventory[name]["docker_image"],
        "image_platform": None,
        "oracle_reward": None,
        "exception": None,
        "agent_sec": None,
        "verifier_sec": None,
        "viability": "not-run",
    }
    if trial_dirs:
        trial = trial_dirs[-1]
        result_path = trial / "result.json"
        if result_path.exists():
            result = json.loads(result_path.read_text())
            reward_txt = trial / "verifier" / "reward.txt"
            if reward_txt.exists() and reward_txt.read_text().strip():
                row["oracle_reward"] = float(reward_txt.read_text().strip())
            if result.get("exception_info"):
                row["exception"] = str(result["exception_info"])[:300]
            for phase, key in (("agent", "agent_sec"), ("verifier", "verifier_sec")):
                pr = (result.get("phase_results") or {}).get(phase) or {}
                if pr.get("duration_sec") is not None:
                    row[key] = pr["duration_sec"]
            if row["agent_sec"] is None:
                aer = result.get("agent_execution") or {}
                s, f = aer.get("started_at"), aer.get("finished_at")
                if s and f:
                    from datetime import datetime
                    row["agent_sec"] = round(
                        (datetime.fromisoformat(f) - datetime.fromisoformat(s)).total_seconds(), 1
                    )
            ver = result.get("verifier_execution") or {}
            s, f = ver.get("started_at"), ver.get("finished_at")
            if s and f and row["verifier_sec"] is None:
                from datetime import datetime
                row["verifier_sec"] = round(
                    (datetime.fromisoformat(f) - datetime.fromisoformat(s)).total_seconds(), 1
                )
        row["image_platform"] = image_arch(inventory[name]["docker_image"])
        if row["oracle_reward"] == 1.0:
            row["viability"] = (
                "rosetta" if row["image_platform"] == "linux/amd64" else "native"
            )
        elif row["exception"]:
            row["viability"] = "failed-infra"
        elif row["oracle_reward"] is not None:
            row["viability"] = "failed-oracle"
        else:
            row["viability"] = "running-or-unparsed"
    rows.append(row)

passing = [r for r in rows if r["viability"] in ("rosetta", "native")]
record = {
    "record": "day1-task-gate",
    "date": "2026-09-01",
    "dataset": "terminal-bench@2.0",
    "git_commit_pin": "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c",
    "gate_command": "harbor run -d terminal-bench@2.0 -a oracle -i <task>... -n 4",
    "pool_seed": pool["seed"],
    "pool_size": pool["pool_size"],
    "n_passing": len(passing),
    "passing_by_difficulty": {
        d: sum(1 for r in passing if r["difficulty"] == d) for d in ("easy", "medium", "hard")
    },
    "passing_categories": sorted({r["category"] for r in passing}),
    "tamper_surface": (
        "tests/ and solution/ are uploaded to the container only at verifier time; "
        "during the agent phase the checker is absent and unreadable/unwritable. "
        "Container network is available by default (allow_internet unset in all task.toml)."
    ),
    "tasks": rows,
}
out = WORK / "day1-task-gate.json"
out.write_text(json.dumps(record, indent=1))
print(f"passing {len(passing)}/{len(rows)}")
for r in rows:
    print(f'{r["viability"]:22s} {str(r["oracle_reward"]):5s} agent={r["agent_sec"]} verif={r["verifier_sec"]} {r["task"]}')
