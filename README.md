# TermScope — Hy3 Process Evaluation on Terminal-Bench 2.0

An individual project for the 2026 Tencent Rhino-Bird open-source practical task, Hunyuan LLM
track, Task 2 (过程评估与错误定位). **This repository is not an official Tencent release.** It runs
[Terminal-Bench 2.0](https://www.tbench.ai) through the Harbor framework (cited; not affiliated
with the benchmark's authors).

**Live site:** https://bingqin2.github.io/hy3-termscope/ · **Report:** [docs/REPORT.md](docs/REPORT.md)

Hy3 drives two unmodified agent scaffolds (`terminus-2`, `mini-swe-agent`) through Harbor on a
pre-registered 20-task Terminal-Bench 2.0 slice, one attempt per (task, configuration) pair. A
three-lane process evaluator then judges *how* each task was attempted — deterministic facts, a
**prefix-replay causal localizer** that re-runs command prefixes in fresh containers with zero
model calls, and an outcome-blinded Hy3 judge — merged under fixed precedence and validated
against blinded reference labels, repeat-session consistency, and a v1→v2 regression card.

## Results in one breath

- **26/40 runs resolved (13/20 per configuration — identical)**; per-difficulty resolve rates
  are also identical across scaffolds; the capability cliff is category-shaped
  (scientific-computing 1/4, data-science and video-processing 0/2 each).
- **12 of 14 failed runs have a material process violation**; the modal first error is a wrong
  interpretive commitment about data that is never re-examined (reasoning 6,
  task_interpretation 3). Two failures have *valid* processes (sound work cut off by the time
  budget). Zero resolved runs had an invalid process.
- **The evaluator's own headline is a negative result**: the outcome-blinded Hy3 judge called
  every completed trajectory `valid` while passing the sabotage-fixture gate and agreeing with
  itself across repeats (38/40) — measured self-evaluation bias, robust to a hardened rubric.
  Localization credibility rests on the replay lane (its one causal flip matches the blinded
  reference label exactly) and on the validation protocol. Full numbers with denominators and
  provenance: [docs/REPORT.md](docs/REPORT.md) §6.

## Run it

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Docker (amd64 images; Rosetta
on Apple silicon), Node 22 for the site, and the Harbor CLI (`uv tool install harbor==0.22.0`).

```bash
uv sync
uv run pytest                                # 73 tests, no network
uv run python scripts/export_results.py      # re-derive every results table byte-stably
uv run python scripts/build_site_data.py     # re-derive the site snapshot (runs the secret scan)
cd frontend && npm ci && npm run dev         # the site on http://localhost:5173
```

Credentials never enter the repo: copy `env.example` to the ignored `.env`; live pipeline steps
read `OPENAI_API_KEY` / `OPENAI_BASE_URL` from the environment. The live stages (campaign,
replay, judge, consistency, regression) are the numbered entry points under `scripts/` and are
documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); their frozen records live under
`data/environment-checks/` and `results/`.

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

Model capability is called exclusively through
[Hy3](https://github.com/Tencent-Hunyuan/Hy3); no training or fine-tuning.

## License

[MIT](LICENSE)
