# Development setup

## What the owner must prepare

| Item | Why | When needed |
| --- | --- | --- |
| **Hy3 API access** — `.env` present (`HY3_API_BASE`, `HY3_AGENT_MODEL`, `HY3_JUDGE_MODEL`); verified live by Day 1's first trial | Agent + judge calls | Day 1 |
| **Disk** — external 2 TB APFS SSD "Elements" (~410 MB/s write verified) hosts Docker's disk image (`/Volumes/Elements/Docker`) and `/Volumes/Elements/termscope-local/` (raw-state archives/exports). Docker needs the SSD attached; to unplug: quit Docker Desktop, then eject. Internal disk: 606 GB free | TB2 task images are large | Verified |
| **amd64 emulation** — verified (`--platform linux/amd64 alpine` runs → `x86_64`); per-task TB2 image viability is still gated on Day 1 | Published TB2 images default to AMD64 | Verified |
| **Python 3.12 + uv** (`brew install uv`) | Backend environment | Day 1 |
| **Harbor CLI** — install per harborframework.com docs; the exact command and version are pinned in the Day 1 environment-check record | Runs TB2 tasks | Day 1 |
| **Node.js + npm** | Frontend build | Day 9 (install anytime) |
| **GitHub Pages enabled** on the repo (Settings → Pages → Source: "GitHub Actions") | Site deploy | Before Day 9's first deploy |
| **Name decision** — repo slug `hy3` collides with Tencent's model name; proposed working title **TermScope** | PDF naming rule | Before first push |
| **Deadline confirmation** | The 10-day sequence + buffer assumes ≈ 2026-09-14 | Now |

## First-time setup

```bash
# Python — pyproject.toml is recreated by Day 1's scaffold; afterwards:
uv sync
uv run pytest

# Harbor — exact pinned install command lives in the Day 1 environment-check record

# Credentials (never committed) — .env already exists; if starting fresh:
cp env.example .env          # then fill in HY3_* values locally

# Frontend (needed from Day 9, harmless earlier)
cd frontend && npm install && npm run dev
```

Note: the template is named `env.example` (no leading dot) because local tooling policy blocks
writing `.env*` paths; the target file you create is still `.env`, which is git-ignored.

## Data and state policy

- `data/` — committed: pre-registered slices, environment-check records, fixture bundles.
- `results/` — frozen sanitized snapshots for the site (committed only on the owner's
  instruction), including `per_run/`, `judge-stability/`, `regression/`.
- `.local/` — raw Harbor trials, judge raw responses (ignored; large state lives on the
  external drive).
- `.env` — credentials (ignored). Nothing secret ever enters git.

## Working policies

- **Git:** nothing is staged, committed, or pushed except on the owner's explicit instruction
  (ROADMAP decision 13).
- **Quota:** real Hy3 calls only in the Day 1 gate trials, the Day 5 judge gate + fixture
  stability sessions, the Day 6 campaign, and Days 7–8 validation; everything else runs on
  fixtures (ROADMAP decision 12 + no-go list).
- **Architecture:** task-image viability (native arm64 / Rosetta / failed) is recorded per task
  at the Day 1 gate; the campaign slice is drawn only from passers.
