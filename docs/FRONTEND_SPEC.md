# Frontend specification

The public face of the project and a first-class deliverable.

## Isolated-page publish workflow (ROADMAP decision 8)

```text
develop site locally against fixture JSON  ->  run the real campaign locally
    ->  freeze results/*.json snapshot     ->  owner approves commit/push
    ->  GitHub Actions builds frontend     ->  GitHub Pages serves the final results page
```

The published page reads only the committed snapshot — no backend, no live pipeline coupling,
fully decoupled from any local machine. Local `npm run dev` is development-only.

## Sections

| Section | Content | Notes |
| --- | --- | --- |
| 01 Leaderboard | Hy3 agent scaffolds (`terminus-2`, `mini-swe-agent`): resolve rate, process-validity rate, per-task wins | single-attempt; no error bars shown or implied |
| 02 Per-task results | slice × config matrix of outcome + process verdicts (resolved / resolved-but-invalid / failed / inconclusive cells) | |
| 03 Failure patterns | taxonomy incidence × severity chart, config overlay | severity weights from EVALUATOR_SPEC §2 |
| 04 Task taxonomy | category / difficulty / origin table for the pre-registered TB2 slice | |
| 05 **Run explorer** | pick any run → step timeline, first-error marker, per-check results, error-type chips, evidence excerpts | **differentiator: process evaluation made visible** |
| 06 Method & validation | localization accuracy, FPR, discriminative results, evaluator v1→v2 regression card (before/after), judge-stability summary; links to the analysis report | credibility page |

Footer: individual Rhino-Bird activity work, which runs Terminal-Bench 2.0 via Harbor (cited).

## Design language (implemented)

sticky mono nav with accent-numbered links, large serif
display headline (Fraunces), numbered sections, thin-bordered tables, warm near-black ground.
Fonts: Fraunces (display), Inter (body), JetBrains Mono (ids, numbers, labels). Wide tables
scroll inside their own containers. No decorative animation before roadmap Day 11 polish.

**Palette — Nature (NPG) hue families, re-stepped for the dark surface** and validated with the
dataviz palette validator (lightness band L 0.48–0.67, chroma ≥ 0.1, CVD ΔE ≥ 8,
normal-vision ΔE ≥ 15, ≥ 3:1 contrast). Raw NPG print hexes fail on dark backgrounds, so the
site uses dark-surface steps of the same hues:

| Role | Token | Hex | NPG family |
| --- | --- | --- | --- |
| ground / surface / line | — | `#14110f` / `#1c1815` / `#2b2521` | — |
| ink / muted / faint | — | `#ece5da` / `#a89e90` / `#7a7166` | — |
| accent (UI chrome only) | `accent` | `#c4502e` | — (infraben-like burnt orange) |
| config A / B / C (categorical, fixed order) | `cat-a/b/c` | `#009db8` / `#bc6f4c` / `#6e72ba` | cyan `#4DBBD5` / salmon `#F39B7F` / blue-gray `#8491B4` |
| pass / partial / fail (status, reserved) | `good/warn/bad` | `#0d8f73` / `#ac9134` / `#b63b32` | teal `#00A087` / ochre / red `#E64B35` |
| severity medium | `sev-medium` | `#937d57` | tan `#B09C85` |

Status cells always pair color with a glyph (✓ / fraction / ✗) — never color alone.

## Data contract

Sample fixtures currently live in `frontend/src/data/*.json` (each carries `"sample": true` and
the page shows a permanent SAMPLE DATA banner). On Day 9 the export script writes the same shapes
to `results/*.json` and the imports switch source — shapes are identical by design. The
shapes carry outcome + process verdicts per task, task `category`, and agent-scaffold config
ids; the sample fixtures are aligned to them before the Day 9 swap:

- `leaderboard.json` — `{sample, updated, rows: [{config_id, label, mean_score, resolve_rate, tasks_won}]}`
- `tasks.json` — `{sample, rows: [{task_id, name, layer, layer_label, difficulty, backend, trap, scores: {config_id: fraction}}]}` (feeds sections 02 and 04)
- `failure_patterns.json` — `{sample, rows: [{error_type, label, severity, count}]}`
- `runs.json` — `{sample, runs: [{run_id, task/config ids, outcome, process, score, first_error_step, error_types, finding, checks, steps}]}`
- `validation.json` — `{sample, localization_exact/pm1: {num, den}, false_positive_rate: {num, den}, discriminative, stability, regression}` (`stability` + `regression` added by the 2026-09-01 rebuild; exact shapes fixed with the Day 10 card, mirrored into the sample fixture first)

Exact shapes are fixed by the Day 1 pydantic contracts; the frontend's `src/types.ts` mirrors
them and never invents fields.

## Stack and deploy

Vite + React + TypeScript + Tailwind v4 (scaffold in `frontend/`). Charts: hand-rolled SVG or
Recharts. Deploy: GitHub Actions workflow (added Day 10) builds with `VITE_BASE=/<repo-slug>/`
and publishes to GitHub Pages; the owner enables Pages (Settings → Pages → Source: GitHub Actions)
before the first deploy. Nothing deploys until the owner approves the commit.
