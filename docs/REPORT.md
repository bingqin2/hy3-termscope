# TermScope — analysis report

Hy3 process evaluation and first-error localization on Terminal-Bench 2.0 (Rhino-Bird Task 2).
Every number in this report is re-derivable from committed artifacts; each section names its
sources. Site: the GitHub Pages deployment of `frontend/` (sections 01–06 mirror this report).

## 1. Headline

Hy3 drove two unmodified agent scaffolds (`terminus-2`, `mini-swe-agent`) through a
pre-registered 20-task Terminal-Bench 2.0 slice, one attempt per (task, configuration) pair:
**26/40 runs resolved (13/20 per configuration — identical resolve rates)**. A three-lane
process evaluator (deterministic facts, prefix-replay causal localization, blinded Hy3 judge)
then judged *how*, and was itself validated against blinded reference labels.

Outcome × adjudicated process (40 runs; provenance: verifier × reference labels + human
adjudication; `results/runs.json`):

| | process valid | partial | invalid | no verdict (honest null) |
| --- | --- | --- | --- | --- |
| **resolved (26)** | 25 | 0 | 0 | 1 |
| **unresolved (14)** | 2 | 5 | 7 | 0 |

Two findings define the report:

1. **Hy3's failures are dominated by reasoning, not by destructive actions.** 12 of 14 failed
   runs have a material process violation; the modal first error is committing to a wrong
   interpretation of observed evidence and never re-examining it. Only one failed run
   destroyed its own task (causally proven by replay); zero resolved runs had an invalid
   process.
2. **Hy3 cannot police itself.** The outcome-blinded Hy3 judge called every completed campaign
   trajectory `valid` — including all 14 failures — while passing the sabotage-fixture gate and
   agreeing with itself across repeat sessions (38/40). A hardened rubric with validator-enforced
   audits did not change this. The measured mode is *audit-then-absolve*: self-evaluation bias
   robust to prompt engineering (§6). Localization credibility in this system therefore rests on
   the deterministic and replay lanes plus blinded labels — a design conclusion, not a caveat.

## 2. Campaign setup

- **Slice**: 20 tasks (3 easy / 11 medium / 6 hard, 14 categories), seeded stratified draw from
  27 oracle-gate passers, frozen with the full protocol before any campaign call
  (`data/slices/slice-v1.json`, `preregistration.json`).
- **Single attempt by design** (integrity choice, pre-registered): no best-of-N, no re-rolls;
  the sole re-run exception (infrastructure failure) was never needed. No error bars are
  claimed on n=1 attempts; rates are raw fractions.
- **Execution**: 40/40 runs completed in 3.55 h wall-clock, zero inconclusive
  (`data/environment-checks/day6-campaign-record.json`). Four incidents (agent time budget ×2,
  model context window, memory-limit SIGKILL) were classified as agent failures under the
  pre-registered outcome policy with evidence in `results/campaign-incidents.json`.
- **Spend**: agents 21.27M tokens; judge lanes ≈ 3.8M total across the official pass,
  consistency sessions, and the v2 regression pass (`results/spend.json`,
  `results/regression/regression-card.json`).

## 3. Outcome results

Per-difficulty resolve rates are **identical for both scaffolds** (per config: easy 2/3,
medium 8/11, hard 3/6), and 16 of 20 tasks are concordant — both configurations resolve or both
fail. The capability boundary on this slice is task-determined far more than scaffold-determined.

| difficulty | terminus-2 | mini-swe-agent | pooled |
| --- | --- | --- | --- |
| easy | 2/3 | 2/3 | 4/6 |
| medium | 8/11 | 8/11 | 16/22 |
| hard | 3/6 | 3/6 | 6/12 |

**Category cliff** (pooled): perfect on data-querying, machine-learning, mathematics,
optimization, personal-assistant, system-administration (2/2 each) and strong on
software-engineering (5/6); collapses on scientific-computing (1/4), data-science (0/2),
video-processing (0/2), file-operations (0/2). The cliff tracks a specific demand: tasks whose
solution hinges on an *interpretive commitment about data* (what an axis, frame, or format
means) that must be checked against domain knowledge rather than against the shell.

**The four discordant tasks** split evenly: terminus-2 alone failed dna-insert and
financial-document-processor; mini-swe-agent alone failed pytorch-model-recovery and
schemelike-metacircular-eval. No scaffold dominance; the discordance looks like sensitivity to
context shape (persistent tmux pane vs fresh-subshell steps), not capability.

**Failure is expensive**: failed runs averaged 881K agent tokens vs 344K for resolved runs
(2.6×) — Hy3 spends most where it is lost, typically in long hypothesis-testing loops after an
early wrong commitment.

## 4. Process results

Reference labels (blinded; 14/14 failed runs; `results/reviews/`): 2 valid / 5 partial /
7 invalid; 12 located first errors; category distribution reasoning 6, task_interpretation 3,
implementation 2, action_execution 1 — similar across scaffolds (terminus-2: 3 reasoning /
2 task_interpretation / 1 implementation; mini-swe-agent: 3 reasoning / 1 each of
task_interpretation, implementation, action_execution).

Two failed runs have **valid processes**: both extract-moves-from-video attempts ran sound
OCR pipelines and were cut off by the official time budget mid-work — failure without process
error, exactly the distinction a process evaluator exists to make.
`correct_result_invalid_process` occurred **zero** times on this slice.

## 5. Case studies

Each case names its run; walk it step-by-step in the site's run explorer or in
`results/per_run/<run>/bundle.json`. First-error steps below are the blinded reference labels.

1. **The same physics mistake, twice** — `raman-fitting`, both configurations (invalid;
   first error step 10 / step 14, reasoning). The spectrum's x-axis is reciprocal
   (1e7/x → cm⁻¹); both agents' own peak detections contained the true G/2D features, and both
   instead assigned the two tallest features — the silicon substrate lines — because their ratio
   loosely matched, then fitted and reported the wrong peaks. Two independent contexts, same
   model, same unexamined commitment: evidence the failure is a model disposition, not a
   sampling accident.
2. **Tuning the pipeline to a wrong belief** — `video-processing`, terminus-2 (invalid; step 16,
   reasoning). The agent misread its own silhouette table (the true jump arc at frames 53–62 was
   in the data it quoted), fixed the search window elsewhere, dismissed contradicting renders as
   a "jump apex pose", then iterated detector heuristics until one reproduced the presupposed
   frames — and called the result "provably safe". A textbook confirmation-loop failure.
3. **Killing its own shell** — `sam-cell-seg`, mini-swe-agent (invalid; step 8,
   action_execution). `pkill -f "pip install"` matches the agent's *own* command shell; the
   agent never diagnosed the -15/-9 returncodes, escalated to `pkill -9 -f pip`, and the run
   ended SIGKILLed by its own broadening pattern — an environment-model failure the fresh-subshell
   scaffold makes especially easy.
4. **The one causal flip, confirmed three ways** — `financial-document-processor`, terminus-2
   (partial; step 12, task_interpretation). The replay lane proved step 12 flips the task from
   completable to not (the only causal flip in the campaign); the blinded reference label
   independently chose step 12; a repeat judge session (1 of 7 on this run) also found step 12;
   the owner's post-reveal adjudication confirmed. Triple-concordant localization — and the
   official judge session still said `valid`.
5. **Failure without error** — `extract-moves-from-video`, both configurations (valid, no first
   error). Sound download→OCR→parse pipelines, iterating extraction heuristics when the time
   budget expired mid-debug. Graded `unresolved` by outcome, `valid` by process — the quadrant's
   bottom-left cell exists.

## 6. Evaluator validation (the evaluator is measured, not trusted)

Protocol: blinded labels on every failed run captured before any evaluator output existed for
the labeler (reviewer registry and a recorded deviation: an independent model rater labeled,
`results/protocol-deviations.json`); fixture gates; repeat-session consistency; one versioned
revision scored by a regression card against the frozen labels
(`data/environment-checks/day7-validation.json`, `results/regression/regression-card.json`).

| measure | result |
| --- | --- |
| localization, merged vs reference (exact; both-'none' counts) | 3/14 |
| localization, reference-located runs only | 1/12 |
| replay's located run vs reference | 1/1 exact |
| judge verdict vs reference (valid vs not) | 2/14 |
| false-positive audit | honest null (0 flagged) |
| fixture gates v1 and v2 | passed |
| judge self-consistency (repeat sessions) | 38/40 · flagged run 5/5 |
| detection of non-valid processes, v1 → v2 | 0/12 → 1/12 |

The negative result is the finding: with near-perfect self-consistency and a passing sabotage
gate, the judge's blanket `valid` on real failures is **systematic leniency**, not noise. The v2
revision (mandatory validator-enforced audits, valid-as-earned semantics, 3.75× wider evidence
window) changed nothing semantically — sampled v2 responses name the fatal commitment, note the
missing correctness check, and absolve anyway (*audit-then-absolve*). The one v2 gain
(detection 1/12) comes from the merge policy capping a semantic `valid` on a causal replay
flip. Interpretation: Hy3 judging Hy3 shares the agent's blind spots — the raman axis error it
absolved as judge is the same error it made as agent. Self-evaluation bias, anticipated in
`EVALUATOR_SPEC.md` §4.8, is here *measured*: robust to rubric hardening, stable across
sessions. The revision loop closed at one iteration by pre-registration; stored campaign
evaluations remain v1.

## 7. Limitations

- **n = 20 tasks × 1 attempt.** Pre-registered scope; no run-to-run variance estimates. Rates
  are raw fractions with explicit denominators everywhere.
- **Reference labels came from an independent model rater** (Claude, different family from the
  judge), not the human owner — a documented protocol deviation. Labels are step-anchored with
  quoted evidence and immutable; the owner adjudicated flagged runs post-reveal. The rater knew
  each labeled run had failed (the judge is outcome-blinded), which inflates the verdict-gap
  comparison by an unknown margin; it cannot explain the localization gap.
- **Replay localizes destructive causality only.** `none` means "no prefix flips oracle
  reachability" — most Hy3 failures are omissions that leave the task completable, which replay
  correctly does not (and cannot) localize.
- **Rosetta emulation** (amd64 images on arm64) inflates wall-clock; three tasks were excluded
  at the gate for emulation-specific breakage; time-budget comparisons with native hardware are
  not claimed.
- **Site truncation**: the run explorer truncates long observations to 1,500 chars per step;
  full trajectories live in the per-run bundles.
- One resolved run has no semantic verdict (judge prompt beyond the gateway's measured 192K-token
  input limit) — reported as an honest null throughout.

## 8. Reproduction

Everything derives from the repo: `uv sync && uv run pytest` (73 tests);
`uv run python scripts/export_results.py` re-derives every table byte-stably from
`results/per_run/`; `uv run python scripts/build_site_data.py` re-derives the site snapshot
(with the publication secret scan); the campaign, replay, judge, consistency, and regression
entry points are under `scripts/` with their records under `data/environment-checks/`.
Credentials only ever enter via environment variables (`env.example`).
