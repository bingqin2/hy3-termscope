# Architecture

The benchmark and agent harness are external, pinned components; this repository builds the
layer on top: import, evaluation, validation, and publication.

## Repository layout

```text
.
├── data/
│   ├── slices/             # pre-registered campaign slice files (ROADMAP decision 15)
│   ├── environment-checks/ # committed Day 1 gate records: per-task arm64/Rosetta viability,
│   │                       #   oracle outcomes, pinned versions and licenses
│   └── fixtures/           # 3 doctored bundles (valid / invalid-known-first-error /
│                           #   inconclusive) + expected oracles — all evaluator development
├── docs/                   # source of truth for scope, design, planning, progress
├── frontend/               # Vite + React + TS + Tailwind static site (FRONTEND_SPEC.md)
├── results/                # frozen sanitized JSON the site reads; per_run/,
│                           #   judge-stability/, regression/ validation records
├── scripts/                # reproducible entry points: gate_tasks, run_trial, import_trial,
│                           #   evaluate_run (verdict-suppressed by default), replay_localize,
│                           #   judge_stability, regression_card, export_results, annotate CLI
├── src/termscope/          # working title — owner may rename (NEXT_STEPS owner item)
│   ├── contracts.py        # pydantic: RunBundle, DeterministicCheck, Finding,
│   │                       #   EvaluationResult, HumanReview (all schema_version-stamped)
│   ├── importer.py         # harbor trial artifacts -> immutable content-hashed bundle
│   ├── evaluator/
│   │   ├── deterministic.py  # facts, outcome policy, tamper/write-aware checks
│   │   ├── replay.py         # prefix-replay causal localizer
│   │   ├── judge.py          # fixed Hy3 judge, evidence validation, honest failure
│   │   ├── merge.py          # precedence policy -> EvaluationResult
│   │   └── metrics.py        # provenance-tagged aggregation
│   └── annotate/           # blinded labeling CLI (reviewer identity, timestamps, append-only versions)
├── tests/                  # offline unit tests; fixtures power evaluator tests
├── env.example             # copy to .env (ignored); undotted name due to local tooling policy
└── .local/                 # (ignored) raw harbor trials, judge raw output — archived to
                            #   /Volumes/Elements/termscope-local/ on the external APFS SSD
```

## Pipeline and data flow

```text
harbor run (TB2 task × Hy3-driven agent: terminus-2 / mini-swe-agent)
        │  produces: trajectory (pinned format, expected ATIF), test output, reward, logs
        ▼
importer -> immutable run bundle (content-hashed artifacts + benchmark/agent/config pins)
        │
        ├──────────────────────────┬──────────────────────────────┐
        ▼                          ▼                              ▼
 deterministic lane          replay localizer               semantic lane
 (no model call)             (no model call)                (one Hy3 judge call)
 verifier facts, outcome     fresh env, replay cmds 1..k,   rubric-v1/prompt-v1,
 policy, tamper + write-     checks per prefix, first       evidence-anchored findings,
 aware facts, claim-vs-      flip = causal candidate,       first_error {location, step},
 evidence                    located|none|unlocatable       honest unavailable/context_limit
        └──────────────────────────┴──────────────┬───────────────┘
                                                  ▼
                              merge policy -> EvaluationResult (versions recorded)
                                                  │
                          blinded label lane (human owner or independent model rater): initial label -> reveal -> human adjudication
                                                  │
                              export_results (provenance-tagged aggregation)
                                                  ▼
                        results/*.json (frozen, committed on the owner's instruction)
                                                  ▼
                        frontend build -> GitHub Pages (isolated results page)
```

## Core contracts (Day 1, `src/termscope/contracts.py`)

All carry `schema_version`; artifact references carry SHA-256 digests.

- **RunBundle** — benchmark pin (dataset registry + revision), task id/category/difficulty,
  agent config (scaffold, Hy3 model settings), trajectory path + digest + format version,
  verifier artifacts (test output, reward, logs), timestamps, environment notes.
- **DeterministicCheck** — check id, status (`pass|fail|warning|unknown`), summary, evidence
  references, `hard_process_failure` flag.
- **Finding** — source (`deterministic|replay|semantic|human`), category (§2 of
  EVALUATOR_SPEC), severity, rationale, `step_id`, evidence references, `recovered` flag.
- **EvaluationResult** — outcome status, process status, `correct_result_invalid_process`,
  `first_error {location: located|none|unlocatable, step_id}`, checks, findings, replay result,
  evaluator/rubric/prompt versions, judge configuration, honest exclusions.
- **HumanReview** — append-only versions; blinded initial label (timestamped before reveal),
  adjudication with per-finding decisions.

## Stack

- **Python 3.12** managed by uv; pydantic (contracts), httpx (Hy3 judge calls), pyyaml, typer
  (CLIs); pytest + ruff for development.
- **Harbor CLI + Docker Desktop** for all task execution; Docker's disk image lives on the
  external APFS SSD ("Elements"); AMD64 task images run under verified emulation; versions
  pinned in the Day 1 environment-check record.
- **Hy3 API** — OpenAI-compatible; the agent receives it through the scaffold's environment
  (`OPENAI_API_KEY`/`OPENAI_BASE_URL` under Harbor); the judge is called directly via httpx;
  agent and judge configured separately via `.env`.
- **Frontend** — Vite + React + TypeScript + Tailwind v4; GitHub Actions builds and deploys
  to GitHub Pages.

## Failure handling principles

- An environment failure (image pull, emulation crash, harness failure not attributable to the
  agent) marks the run `inconclusive` — excluded from accuracy metrics, never blamed on the
  agent; the judge is skipped (quota).
- Runs that hit the scaffold's turn/time caps still import as valid, gradeable bundles.
- Judge failures degrade honestly: schema-invalid after one retry → semantic lane
  `unavailable`; oversized trajectory → `context_limit`; the deterministic verdict stands.
- Command outputs inside trajectories are untrusted data — delimited as evidence for the judge,
  never interpreted as instructions (EVALUATOR_SPEC §4).
- Replay that cannot reproduce a flip reports `unlocatable` with the non-determinism recorded —
  never a guessed step.
