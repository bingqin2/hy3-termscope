# TermScope — Hy3 Process Evaluation on Terminal-Bench 2.0

Agent benchmarks grade the final state: run the verifier, pass or fail. TermScope asks the
question that bit cannot answer — **was the agent's *process* sound, and if not, at exactly
which step did it first go wrong?** It runs Tencent's Hy3 model as a terminal agent on 20
Terminal-Bench 2.0 tasks, records every reasoning / command / observation step, evaluates each
trajectory with a three-lane process evaluator, and — before trusting any of that — validates
the evaluator itself against blinded reference labels. The headline finding is a carefully
measured negative result about LLM self-evaluation.

**Live site:** https://bingqin2.github.io/hy3-termscope/ · **Full report:** [docs/REPORT.md](docs/REPORT.md)

Individual entry for the 2026 Tencent Rhino-Bird practical task (Hunyuan LLM track, Task 2:
process evaluation and error localization) — **not an official Tencent release**. Tasks come
from [Terminal-Bench 2.0](https://www.tbench.ai) (pinned revision), executed through the Harbor
CLI; all model capability is called through
[Hy3](https://github.com/Tencent-Hunyuan/Hy3) — no training or fine-tuning.

## Headline results

40 runs: 20 pre-registered tasks × 2 unmodified agent scaffolds (`terminus-2`,
`mini-swe-agent`), one attempt per pair by design.

- **Outcomes.** 26/40 runs resolved — 13/20 for *each* scaffold, and identical per difficulty
  tier (easy 2/3, medium 8/11, hard 3/6). Swapping the scaffold changed *which* tasks were
  solved, never *how many*: the capability boundary is category-shaped (scientific-computing
  1/4; data-science and video-processing 0/2 each), so it sits in the model, not the scaffold.
- **Processes.** Blinded labels find a material process violation in 12 of the 14 failed runs.
  The modal first error is not a bad command — it is a wrong interpretive commitment about the
  task or data that is never re-examined. Two failures had sound processes cut off by the time
  budget, and zero resolved runs had an invalid process.
- **Error localization.** The prefix-replay lane produced one causally *proven* first error:
  replaying the trajectory's commands shows the task still completable before step 12 and
  unrecoverable from it — and that step matches the blinded reference label exactly.
- **The negative result.** The outcome-blinded Hy3 judge rated all 39 completed trajectories
  `valid` — while passing a sabotage-fixture gate and agreeing with itself on 38/40 repeat
  sessions. That is systematic self-evaluation leniency, not noise, and it survived a hardened
  v2 rubric with mandatory audits: the judge performs the audits, then absolves anyway
  ("audit-then-absolve"). The only detection gain in v2 came from capping the judge's verdict
  with causal replay evidence. Full numbers with denominators and provenance:
  [docs/REPORT.md](docs/REPORT.md) §6.

## How it works — the design in six steps

The core credibility problem is circular: the same model family acts and judges. Every design
choice below exists to break that circle with evidence that is not a model's opinion.

1. **Freeze the benchmark before spending a single API call.** A seeded, stratified 20-task
   slice (official difficulty tiers × task categories) is drawn from the gate-passing pool and
   committed as a pre-registration, so results cannot be cherry-picked afterwards
   (`scripts/select_slice.py`, frozen in `data/slices/`).
2. **Run once, record everything.** Each (task, scaffold) pair gets exactly one attempt — no
   best-of-k — via Harbor with identical flags; every step lands in a pinned trajectory format
   (`scripts/run_campaign.py`).
3. **Evaluate with three independent lanes.**
   *Deterministic facts* — protected-file writes, failed-command streaks, command loops,
   unverified success claims; zero model calls.
   *Prefix-replay causal localization* — re-run the first *k* commands in a fresh container and
   test whether the task is still completable from that state; the earliest *k* that flips
   completability is a causally confirmed first error, again with zero model calls
   (`scripts/replay_campaign.py`).
   *Blinded Hy3 judge* — the model reads the trajectory with the outcome withheld and must
   anchor every claim to step citations (`scripts/evaluate_campaign.py`).
4. **Merge with causal precedence.** Replay evidence outranks judge opinion; anything unknown
   stays an explicit `unlocatable` / honest null rather than a guess
   (`scripts/assemble_evaluations.py`).
5. **Validate the evaluator itself.** All 14 failed runs are labeled under a blinded,
   append-only review protocol before any evaluator output is revealed (`scripts/annotate.py`);
   40 repeat judge sessions measure self-consistency (`scripts/consistency_sessions.py`);
   sabotage fixtures gate every judge version.
6. **Score any change against frozen labels.** The single permitted rubric revision (v2) is
   scored on a regression card against the frozen blinded labels — detection moved 0/12 → 1/12,
   and only via the causal cap. That controlled comparison is what isolates the negative result
   above (`scripts/regression_card.py`).

## Reproduce it

### Tier 1 — verify the analysis from committed artifacts (no API key, ~2 minutes)

Every number on the site and in the report is re-derived from committed artifacts under
`results/` and `data/`; a clean clone has been verified to rebuild every results table
byte-identically.

```bash
uv sync
uv run pytest                             # 73 tests, no network
uv run python scripts/export_results.py   # rebuild results/*.json — byte-identical to committed
uv run python scripts/build_site_data.py  # rebuild the site snapshot (+ publication secret scan)
cd frontend && npm ci && npm run dev      # the site on http://localhost:5173
```

### Tier 2 — re-run the full campaign (Hy3 API access + Docker required)

Copy `env.example` to the git-ignored `.env` and fill in the Hy3 endpoint, key, and model
names — credentials only ever live in the environment, never in the repo. Then, in order:

```bash
uv run python scripts/run_campaign.py          # 40 Harbor jobs from the frozen pre-registration
uv run python scripts/evaluate_campaign.py     # import trials; deterministic + judge lanes
uv run python scripts/replay_campaign.py       # causal replay lane (Docker, zero model calls)
uv run python scripts/assemble_evaluations.py  # merge lanes into immutable evaluations
```

The validation stages are runnable too (they spend judge quota): `scripts/annotate.py` for
blinded labeling, `scripts/consistency_sessions.py` for repeat sessions,
`scripts/regression_card.py` for the v2 card. Stored campaign artifacts are immutable by
design: a re-run writes fresh artifacts instead of overwriting the frozen ones.

**Environment:** Python 3.12 with [uv](https://docs.astral.sh/uv/), Docker (amd64 images;
Rosetta on Apple silicon), Node 22 for the site, and the Harbor CLI
(`uv tool install harbor==0.22.0`).

## Repository layout

```text
.
├── data/            # pre-registered slice + protocol, environment/gate/validation records, fixtures
├── docs/            # report, requirements audit, roadmap, specs, next steps
├── frontend/        # static results site (Vite + React + TS + Tailwind) — reads its committed snapshot
├── results/         # per-run bundles + lanes, reviews, exports, judge-stability, regression card
├── scripts/         # reproducible pipeline entry points (campaign → lanes → exports → site data)
├── src/termscope/   # contracts, importer, evaluator (deterministic / replay / judge / merge)
├── tests/           # 73 automated tests (evaluator logic is API-free under test)
├── env.example      # copy to .env (ignored) and fill locally
└── 犀牛鸟开源-实战任务-混元大语言模型项目.pdf   # original instruction file
```

## Documentation

- [Analysis report](docs/REPORT.md) — headline quadrant, case studies, validation, limitations
- [Project requirements & audit](docs/PROJECT_REQUIREMENTS.md) — every deliverable with evidence
- [Evaluator specification](docs/EVALUATOR_SPEC.md) · [Architecture](docs/ARCHITECTURE.md)
- [Roadmap & decisions](docs/ROADMAP.md) · [Next steps](docs/NEXT_STEPS.md)
- [Development setup](docs/DEVELOPMENT_SETUP.md) · [Frontend spec](docs/FRONTEND_SPEC.md)

## License

[MIT](LICENSE)
