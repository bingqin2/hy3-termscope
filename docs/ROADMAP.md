# Roadmap

**process evaluation and first-error localization of Hy3 agents on
Terminal-Bench 2.0, run through Harbor**, with a hybrid deterministic + replay + Hy3-judge
evaluator validated against blinded human labels, published on a GitHub Pages site. The
benchmark and harness are proven public components, so build effort concentrates on the graded
core — the evaluator — and TB2's fast task checks keep prefix-replay localization viable.
Requirements: [PROJECT_REQUIREMENTS.md](PROJECT_REQUIREMENTS.md).


## Verified environment facts

- **Hy3 gateway** (verified live): OpenAI-compatible chat completions at the configured base
  URL (`.env`); reasoning is always on (~140–150 tokens minimum per reply — `max_tokens` must
  leave room for it); JSON-object mode and native `tool_calls` both work.
- **This machine**: amd64 container emulation verified (published TB2 images default to AMD64;
  per-task viability is still gated on Day 1); internal disk 606 GB free; Docker's disk image
  and `termscope-local/` raw-state archives live on the external 2 TB APFS SSD "Elements"
  (~410 MB/s write verified) — Docker requires the SSD attached, and unplugging it means
  quitting Docker Desktop first, then ejecting.

## Day 1 gate — facts to verify before anything is frozen

Verified on this Mac and written as committed environment-check records before the Day 2 freeze:

- Harbor runs TB2 locally: oracle-agent trial per candidate task, with per-task
  **native-arm64 / Rosetta-emulated / failed** status recorded (TB2 images default to AMD64).
- Hy3 drives `terminus-2` through the OpenAI-compatible environment (fallback `mini-swe-agent`,
  proven to work with Hy3 under Harbor).
- The emitted trajectory format (expected ATIF; exact version pinned) and the per-trial
  artifact inventory (trajectory, test output, reward, logs) suffice for the evaluator.
- The in-container tamper surface: whether the agent can see or modify the task's tests.
- Per-run token cost and wall-clock → campaign sizing (quota is not binding; time is).

## Fixed execution decisions

Change one only after recording the implementation evidence that forced the change.

1. **Benchmark: Terminal-Bench 2.0 through Harbor, pinned.** Dataset registry + revision and
   component licenses recorded on Day 1, attributed in README and report. No benchmark
   construction. The standard answer is each task's shipped verifier; oracle solutions are used
   only for environment gates and human-adjudication reference.
2. **Existing agent scaffolds only.** Primary config `terminus-2` (neutral single-tool bash
   agent); second config `mini-swe-agent` — both locked in. No own agent, no scaffold
   modification beyond configuration. The scaffold comparison is the leaderboard axis.
3. **Hy3 everywhere.** The solving agent and the semantic judge are both Hy3 (separately
   configured, both recorded per run). No other model anywhere.
4. **The trajectory format is what Harbor emits, pinned (expected ATIF).** No competing schema.
5. **Evaluation is hybrid and deterministic-first.** Executable verifier facts and trajectory
   facts establish truth; the replay localizer establishes causality; the Hy3 judge interprets
   meaning; merges resolve conflicts toward deterministic evidence.
6. **Every semantic finding must cite evidence.** Citations are validated against the bundle;
   one schema-repair retry, then honest failure — never a fabricated verdict.
7. **Prefix-replay causal localization is the flagship contribution.** For every failed or
   flagged run: rebuild the task environment fresh, replay the trajectory's commands 1..k per
   prefix, run the task's checks at each prefix; the first flip is the causal first-error
   candidate. Localization values `located | none | unlocatable`; non-determinism recorded,
   never hidden. Replay outranks the judge on step localization; per-task replay feasibility is
   recorded at the gate.
8. **GitHub Pages is the canonical frontend; the published page is isolated from the pipeline.**
   The static site reads only a frozen committed `results/*.json` snapshot; local `npm run dev`
   is development-only. The resume URL is the Pages site.
9. **No secrets in the repo.** Hy3 credentials via environment variables; `env.example`
   documents them; `.env` is ignored.
10. **README and site footer state:** individual Rhino-Bird activity work; not an official
    Tencent release; runs Terminal-Bench 2.0 via Harbor (cited; not affiliated with the
    benchmark's authors).
11. **Frontend is layout-inspired, not copied.** Own code, styling, and name.
12. **Run-once, no-repeat campaign.** Full pre-registered coverage; each test runs exactly once
    and the first result is final: no re-rolls, no best-of-N, no cherry-picking (bundles are
    immutable by construction). One judge evaluation per stored trajectory (its schema-repair
    retry fixes format, never the verdict). Sole exception: a run invalidated by measurement
    failure (Docker/API infrastructure, marked `inconclusive` with the broken attempt kept on
    record) may be re-run once — apparatus failures are re-measurable, disliked results are not.
    *Carve-out:* pre-registered instrument-measurement sessions (the ten judge-stability
    sessions and the one-repeat-per-run consistency check, EVALUATOR_SPEC §6) repeat judge
    calls to measure the *instrument's* variance, never to change a result; the first
    evaluation remains official and repeats live separately under `results/judge-stability/`.
13. **Git control stays with the owner.** Staging, committing, or pushing happens only on the
    owner's explicit instruction in that moment — never as a side effect of finishing work.
14. **Broad and deep — quota is not the constraint (owner-confirmed 2026-09-01).** The slice
    takes every gate-passing task (target 16–20, floor 12) × both configs, **single attempt
    per test** — the owner's explicit choice: no repeated-run experiments, decision 12 stands.
    Full validation depth: blinded labels, judge stability, per-run consistency sessions, the
    regression card. Sizing is governed by wall-clock and human labeling time, not tokens; if
    gradeable failed runs exceed ~25, a pre-registered seeded subset receives human labels.
15. **Campaign pre-registration.** One committed file freezes, before the first campaign call:
    the task list (seeded stratified selection over difficulty × category from the gate-passing
    pool, candidate order recorded), the config list, the run order, the substitution rule
    (decision 12's infrastructure exception, verbatim), the quota plan, and the blinding
    protocol — alongside the committed gate records.
16. **Versioned evaluator + regression card.** Day 7's measured failure modes drive at most one
    versioned evaluator revision (v2). The regression card re-evaluates the stored campaign
    bundles under v2 against the frozen human labels — deterministic and replay lanes re-run
    free; judge re-calls scoped to runs where the semantic lane was load-bearing — and reports
    detection, false positives, and exact/±1 localization before and after. Stored campaign
    evaluations are never modified. If v1 measures clean, the card records that as final; the
    loop is self-scoping.
17. **Blinded human validation is mandatory and tool-enforced.** The evaluation script
    suppresses verdicts by default (`--show-verdict` required to print one); initial labels are
    timestamped before any reveal; reviews are append-only versions; non-blinded reviews are
    marked and excluded from validation metrics by construction.

## Pipeline (fixed MVP)

```text
harbor run (TB2 task × Hy3 agent) -> trial artifacts (trajectory, test output, reward, logs)
    -> import -> immutable content-hashed run bundle
    -> deterministic lane -> replay localizer -> semantic (Hy3 judge) lane -> merged evaluation
    -> frozen results/*.json -> static site (GitHub Pages) + analysis report
```

## Outcome sequence (10 working days + buffer, assumed submission ≈ 2026-09-14 — unconfirmed)

| Status | Day | Objective | Exit condition |
| --- | --- | --- | --- |
| **Current** | **1 — Environment gate & contracts** | Harbor + TB2 on this Mac (disk headroom + amd64 emulation pre-verified 2026-09-01); oracle trials over ~25–30 candidate tasks with per-task viability records; one live Hy3 + `terminus-2` trial end-to-end; pin trajectory format + licenses; pydantic contracts (bundle, evaluation, review); import the live trial | One Hy3-driven TB2 run imported as a schema-valid, hash-verified bundle; environment-check records written; per-run token cost measured |
| Pending | **2 — Slice pre-registration & fixtures** | Seeded stratified slice (target 16–20 tasks, floor 12, over 3 tiers × ≥ 6 categories from the gate-passing pool); pre-registration file (decision 15); three fixture bundles (valid / invalid-with-known-first-error / inconclusive) doctored from copies of real trials | Slice + gate records ready for the owner's commit; fixtures validate offline against expected oracles |
| Pending | **3 — Deterministic lane** | Identity/hash checks, trajectory validation, verifier parsing, outcome policy (`resolved`/`unresolved`/`inconclusive`), tamper-surface + write-aware facts, claim-vs-evidence comparison, unit tests | Fixtures produce correct deterministic verdicts with zero model calls; a read-only reference to a protected target provably does **not** flag |
| Pending | **4 — Replay localizer** | Fresh-environment rebuild, prefix replay, per-prefix checks, first-flip detection, `located/none/unlocatable`, non-determinism recording | Replay pinpoints the invalid fixture's known step; replay runtime measured on one real trial |
| Pending | **5 — Semantic lane & judge gate** | rubric-v1 + prompt-v1 (taxonomy §2, exploration/recovery, `unlocatable`), evidence validation, retry, merge policy; judge-stability harness | Judge reproduces the fixture oracles (valid → zero findings; invalid → known step + type); 5 stability sessions on the invalid fixture recorded |
| Pending | **6 — Campaign** | Single pre-registered pass (slice × both configs, sequential); aggregation + `results/*.json` export | All bundles stored; every table re-derivable by one script; token/wall-clock spend recorded |
| Pending | **7 — Blinded human validation** | Initial labels on every gradeable failed run before reveal; FP audit of every flagged-resolved run; discriminative fixture check; 5 stability sessions on one real flagged run; one consistency judge session per campaign run | Localization (exact/±1, three-way replay × judge × human), FPR, discriminative, and consistency-agreement numbers with denominators + provenance; evaluator-v1 failure modes documented |
| Pending | **8 — Evaluator v2 & regression card** | Fix the measured failure modes as one versioned revision; regression card vs frozen labels (decision 16); begin site data swap | Card stored under `results/regression/`; stored campaign evaluations untouched; a clean v1 documented as final if nothing needed fixing |
| Pending | **9 — Site & deploy** | Real `results/*.json` (incl. stability + regression data), relabel sections for TB2, Pages deploy workflow, responsive polish | Site live on GitHub Pages from committed JSON; a visitor can walk one failed run to its first error without reading JSON |
| Pending | **10 — Report, audits, demo, freeze** | Analysis report (headline quadrant, case studies, difficulty/category analysis, limitations); requirements-audit walk with per-item evidence pointers; clean-clone no-`.env` verification; security/hygiene scan; README finalization; ≤ 2-min demo | A reviewer can clone, configure `.env`, reproduce the documented path, and view the demo; every checklist item carries an evidence pointer |

## Daily control rule

At each day's end: record the achieved exit condition and broken assumptions; update only the
next day in [NEXT_STEPS.md](NEXT_STEPS.md); preserve raw errors instead of hiding incomplete
integration; unresolved external behavior becomes a bounded spike, not a new research topic.

## Cut order (if the schedule slips)

1. The per-run consistency sessions (the ten judge-stability sessions stay).
2. Escalation re-review of disputed runs.
3. Slice back toward the floor: 16–20 → 12 (all three tiers and ≥ 4 categories still covered).
4. The second agent config (`mini-swe-agent`) — floor: one config; the leaderboard becomes a
   per-task × difficulty story.
5. Site polish beyond the responsive dark theme.

**Never cut:** automatic verification, replay localization, the taxonomy,
resolved-but-invalid-process handling, blinded human validation records, the ten judge-stability
sessions, the regression card, difficulty/boundary analysis, reproducibility scripts, README,
the 2-minute demo, the requirements-audit walk and clean-clone verification, or site sections
01/02/05.

## No-go decisions

- No non-Hy3 model anywhere in the pipeline.
- No benchmark construction; no second benchmark; no own agent scaffold (decisions 1–2).
- No fabricated verdict on judge failure; no finding citing nonexistent evidence.
- No fixture presented as campaign evidence.
- No credentials or personal data in the repo or the published site.
- No new direction after the Day 2 freeze.
- No `git add`/`commit`/`push` without the owner's explicit instruction (decision 13).
- No real-quota Hy3 calls outside the Day 1 gate trials, the Day 5 judge gate + fixture
  stability sessions, the Day 6 campaign, and Days 7–8 validation (real-run stability sessions
  + the scoped v2 re-judging).
- No implication of affiliation with Tencent, the Laude Institute / Terminal-Bench authors.

## Risks

| Risk | Mitigation |
| --- | --- |
| arm64 viability of TB2 task images (published images default to AMD64) | amd64 emulation verified working 2026-09-01 (alpine smoke test); Day 1 gate over ~25–30 candidates with per-task native/emulated/failed records; slice drawn only from passers |
| `terminus-2` ↔ Hy3 gateway mismatch | Day 1 live trial; fallback `mini-swe-agent`, proven with Hy3 under Harbor |
| Replay infeasible on some tasks (non-determinism, interactivity, slow checks) | Per-task feasibility recorded at the gate; honest `unlocatable`; judge + human cover those runs; never silently skipped |
| Long trajectories exceed the judge's context | Fixed head+tail truncation rule, honest `context_limit` result |
| Wall-clock at full breadth (campaign + replay runtime) | Sequential campaign sized by Day 1 per-run timing; replay scoped to failed/flagged runs only; slice floor 12 and the cut order as pressure valves. Quota is not a constraint (owner-confirmed); per-run cost still recorded |
| Deadline unconfirmed | 10 working days + buffer against ≈ 2026-09-14; owner to confirm |

## Prior art and differentiation

**Terminal-Bench 2.0 + Harbor** (tbench.ai; the Harbor framework; 89 tasks, 16 categories,
3 difficulty tiers; licenses recorded at pin time): benchmark and harness reused as-is with
citation. This project adds the process-evaluation layer on top and contributes nothing to, and
claims nothing from, the benchmark itself.
