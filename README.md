# TermScope — Hy3 Process Evaluation on Terminal-Bench 2.0 (working title)

An individual project for the 2026 Tencent Rhino-Bird open-source practical task, Hunyuan LLM
track, Task 2 (过程评估与错误定位). **This repository is not an official Tencent release.** It runs
[Terminal-Bench 2.0](https://www.tbench.ai) through the Harbor framework (cited; not affiliated
with the benchmark's authors).

Hy3 drives existing terminal agents (`terminus-2`, optionally `mini-swe-agent`) through Harbor
on a pre-registered slice of Terminal-Bench 2.0 tasks, producing full step-by-step trajectories.
A process-level evaluation system then judges *how* each task was solved: a deterministic facts
lane, a **prefix-replay causal localizer** that pinpoints the first error with zero model calls,
and an evidence-anchored Hy3 judge — merged under fixed precedence, then validated against
blinded human labels, judge-stability sessions, and an evaluator v1→v2 regression card. Results
are published as an isolated static leaderboard site on GitHub Pages.

## Current status

- **Day 1 — environment gate & contracts — is the active milestone; not started.**

See [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) for the current implementation slice.

## Repository layout

```text
.
├── data/            # pre-registered slices, environment-check records, fixture bundles
├── docs/            # requirements, roadmap, design, decisions, next steps
├── frontend/        # static results site (Vite + React + TS + Tailwind)
├── results/         # frozen sanitized snapshots the published site reads
├── scripts/         # reproducible pipeline entry points
├── src/termscope/   # importer, evaluator (deterministic / replay / judge / merge), annotation
├── tests/           # automated tests
├── env.example      # copy to .env (ignored) and fill locally
└── 犀牛鸟开源-实战任务-混元大语言模型项目.pdf   # original instruction file
```

## Documentation

- [Documentation index](docs/README.md)
- [Project requirements](docs/PROJECT_REQUIREMENTS.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Evaluator specification](docs/EVALUATOR_SPEC.md)
- [Frontend specification](docs/FRONTEND_SPEC.md)
- [Development setup](docs/DEVELOPMENT_SETUP.md)

## Development

Python 3.12 (uv-managed) + the Harbor CLI + Docker Desktop for the pipeline; Node for the
frontend. See [docs/DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md).

**Do not add real credentials to this repository.** Copy `env.example` to the ignored `.env` and
set Hy3 credentials locally. Model capability is called exclusively through
[Hy3](https://github.com/Tencent-Hunyuan/Hy3); no training or fine-tuning.

## License

[MIT](LICENSE)
