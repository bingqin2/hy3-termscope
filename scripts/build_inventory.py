"""Build a task inventory for terminal-bench@2.0 from the pinned checkout."""
import json
import sys
import tomllib
from pathlib import Path

SRC = Path.home() / "termscope-work" / "tb2-src"
OUT = Path.home() / "termscope-work" / "tb2-inventory.json"

rows = []
for task_dir in sorted(SRC.iterdir()):
    toml_path = task_dir / "task.toml"
    if not task_dir.is_dir() or not toml_path.exists():
        continue
    with open(toml_path, "rb") as f:
        t = tomllib.load(f)
    meta = t.get("metadata", {})
    env = t.get("environment", {})
    row = {
        "name": task_dir.name,
        "difficulty": meta.get("difficulty"),
        "category": meta.get("category"),
        "tags": meta.get("tags", []),
        "agent_timeout_sec": (t.get("agent") or {}).get("timeout_sec"),
        "verifier_timeout_sec": (t.get("verifier") or {}).get("timeout_sec"),
        "allow_internet": env.get("allow_internet"),
        "docker_image": env.get("docker_image"),
        "build_timeout_sec": env.get("build_timeout_sec"),
        "cpus": (env.get("resources") or {}).get("cpus") or env.get("cpus"),
        "memory_mb": (env.get("resources") or {}).get("memory_mb") or env.get("memory_mb"),
        "gpus": (env.get("resources") or {}).get("gpus") or env.get("gpus"),
        "has_dockerfile": (task_dir / "environment" / "Dockerfile").exists(),
        "has_encrypted_payload": any(task_dir.rglob("*.enc")),
        "instruction_bytes": (task_dir / "instruction.md").stat().st_size
        if (task_dir / "instruction.md").exists()
        else None,
    }
    rows.append(row)

OUT.write_text(json.dumps(rows, indent=1))

by = {}
for r in rows:
    key = (r["category"], r["difficulty"])
    by.setdefault(key, []).append(r["name"])
print(f"{len(rows)} tasks")
for (cat, diff), names in sorted(by.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
    print(f"{cat:28s} {str(diff):8s} {len(names):2d}  {', '.join(names[:4])}{'...' if len(names) > 4 else ''}")

gpu = [r["name"] for r in rows if r["gpus"]]
net = [r["name"] for r in rows if r["allow_internet"]]
enc = [r["name"] for r in rows if r["has_encrypted_payload"]]
print("\ngpu tasks:", gpu or "none")
print("internet tasks:", net or "none")
print("encrypted payload:", len(enc), "tasks")
sys.stdout.flush()
