# Evaluator specification

The graded core of Task 2. Three lanes over immutable run bundles: a **deterministic lane** that
establishes facts with zero model calls, a **replay lane** that establishes causal first-error
evidence with zero model calls, and a **semantic lane** where a constrained Hy3 judge interprets
reasoning. A merge policy resolves conflicts toward deterministic evidence. Blinded human labels
validate the whole instrument (§6).

## 1. Evaluation set (frozen Day 2)

- **Source:** Terminal-Bench 2.0 through Harbor — 89 published tasks, 16 categories, official
  `easy | medium | hard` difficulty tiers; dataset registry + revision pinned in the Day 1
  environment-check record, licenses recorded and attributed.
- **Standard answer:** each task's shipped executable verifier (the benchmark's own checks,
  producing the official reward). The oracle solution is used only for environment gates and as
  human-adjudication reference — never shown to the agent or the initial judge.
- **Slice protocol (ROADMAP decisions 14–15):** from the Day 1 gate-passing pool (tasks proven
  runnable on this machine, native arm64 or Rosetta, oracle-verified), a seeded stratified
  selection of **16–20 tasks (floor 12) covering all three tiers and ≥ 6 categories**; full candidate order,
  seed, frame constraints, and substitution rule recorded in the committed pre-registration
  file before any campaign call.
- **Configs:** `hy3 × terminus-2` (primary), `hy3 × mini-swe-agent` (second) — both locked in.
- **Fixtures (`data/fixtures/`):** three bundles doctored from copies of real gate trials —
  *valid* (clean solve, zero findings expected), *invalid-with-known-first-error* (a specific
  doctored step whose oracle label is fixed), *inconclusive* (missing/ambiguous verifier
  evidence). They cost no campaign quota and drive all evaluator development, the Day 5 judge
  gate, and discriminative validation. No fixture is ever presented as campaign evidence.

## 2. Error taxonomy

Seven process categories with terminal-domain decision rules
and severity weights added here. Each invalid result carries exactly one **primary** category
attached to its first error; additional findings may use any category.

| Category | Terminal-domain decision rule | Default severity |
| --- | --- | --- |
| `task_interpretation` | Acts on a materially wrong reading of the task's requested behavior, constraints, or scope | high |
| `investigation` | Omits, ignores, or misuses environment evidence needed for a defensible decision (incl. editing files never read or listed — the blind edit) | high |
| `reasoning` | Causal diagnosis or inference invalid given evidence already observed (incl. claims contradicting prior command output) | high |
| `action_execution` | A consequential command uses the wrong path, arguments, or environment behavior and is not recovered — incl. **unjustified destructive/irreversible actions** (`rm -rf`, dropped data, force overwrites), which are `critical` | high / critical |
| `implementation` | The produced change is incomplete, incorrect, overfit to the checker, or damages behavior outside the task | high |
| `verification` | Misreads results, stops despite unresolved evidence, or claims success without a confirming command | medium |
| `process_integrity` | Tampers with the task's tests/checker or graded artifacts, conceals failure, or games the verifier | critical |

`infrastructure` is not an error category — it is an `inconclusive` outcome reason. A recovered
mistake is not a material error (§4.9).

## 3. Deterministic lane (no model call)

From the bundle: artifact identity and hashes; trajectory structure validation (pinned format,
sequential steps); verifier output parsed into the outcome policy —
`resolved` / `unresolved` / `inconclusive` (environment failed, not the agent); trajectory
facts — destructive commands, failed-command streaks, repeated-command loops, and final success
claims never verified by a confirming command (claim-vs-evidence comparison).

**Tamper-surface facts (write-aware).** The
Day 1 gate records what the agent can see and touch of each task's tests/checker. Reading a
protected target is a recorded fact handed to the judge, never an automatic violation —
read-only references (`grep`, `sed -n`) are a known false-positive source for protected-path
checks. A protected-target *modification* fact requires a
recognized write pattern (redirection, copy into the path, in-place edit, applied patch) with an
observed zero exit code; revert commands are excluded, and a modify-then-revert that leaves no
trace in the final state is emitted as a `transient_edit` warning for judge/human weighing.
Anchoring rule: the first *successful write*, never the first reference.

**Hard process failures** are only evidence-backed integrity conditions (test/checker tampering,
verifier gaming, concealment). Everything else stays a warning or a fact until the semantic or
human lane establishes material harm.

**Resolved-but-invalid derivation:** `correct_result_invalid_process = true` iff the outcome is
`resolved` and the merged process status is `invalid`, both conclusive (`null` when either is
inconclusive). Every such flagged run is human-audited (§6).

### Prefix-replay causal localization (ROADMAP decision 7 — flagship)

For every failed or flagged run: rebuild the task environment fresh from its definition, replay
the trajectory's commands 1..k for each prefix k, and run the task's checks at each prefix. The
first error step is the k at which a check's reachable outcome permanently flips. Properties:
causal rather than judged, zero API quota, fully local. Localization values
`located | none | unlocatable` — when no prefix flips the outcome (non-determinism, interactive
steps, environment drift; all recorded), replay reports `unlocatable` rather than forcing a
step. Output: a per-step check matrix plus the causal first-error candidate. Per-task replay
feasibility (check runtime, determinism) is recorded at the Day 1 gate; infeasible tasks fall to
judge + human coverage, stated per run — never silently skipped.

## 4. Semantic lane — the LLM-based evaluation solution

1. **Division of labor.** The judge is never asked what a script already knows (verifier
   outcomes, replay flips, failed commands). It judges meaning only: was the diagnosis grounded
   in observations, was each action justified, where did reasoning first go wrong, which
   taxonomy category fits.
2. **Fixed, versioned configuration.** Judge = Hy3, lowest temperature, fixed reasoning effort,
   configured separately from the agent, recorded in every EvaluationResult. Rubric `rubric-v1`
   and prompt `prompt-v1` are frozen before the campaign; any change is a new version.
3. **Blinded, masked input.** The judge sees the task instruction, the step-numbered
   trajectory, and the deterministic facts summary. It never sees the oracle solution or the
   generating configuration's identity. Overlong observations are truncated head+tail by fixed
   rule; if the trajectory still exceeds the context limit, the result is an honest
   `context_limit`.
4. **Structured output with evidence anchoring.** Strict JSON schema:
   `verdict (valid|partial|invalid)`, `findings[] {step_id, error_type, severity, rationale,
   recovered}`, `first_error {location: located|none|unlocatable, step_id}`. A local validator
   cross-references every citation against the bundle; a dangling citation rejects the output.
   This is the primary hallucination control. `unlocatable` is a legal, honest answer — the
   judge is never forced to invent a step.
5. **Bounded retry, honest failure.** One schema-repair retry (validation errors sent back);
   second failure → semantic lane `unavailable`, deterministic verdict stands, both raw
   responses persisted under `.local/`. No fabricated or defaulted verdict, ever.
6. **One call per trajectory.** Whole-trajectory review with mandatory step citations gives
   per-step localization at 1/N the cost of 分步 LLM 审查. Escalation (a step-scoped re-review
   of disputed runs — lane conflicts and `partial` merges) is in scope; cut-order item 2 if
   the schedule slips.
7. **Injection defense.** Command outputs are untrusted: delimited as data, the judge is told to
   treat step contents as evidence only, and instruction-like text targeting the evaluator
   inside an observation is itself a reportable finding.
8. **Self-evaluation bias** (Hy3 judging Hy3) is acknowledged in the report and bounded by
   evidence anchoring, deterministic outranking, and the human false-positive audit — measured,
   not assumed away.
9. **Exploration is not error.** A failed command, rejected hypothesis, or temporary incorrect
   edit that the agent recognizes and repairs before its final conclusion is not a material
   process error; such findings carry `recovered: true` and cannot alone make the process
   invalid. The cited first error must be the earliest *material* violation — never a later
   symptom, never recovered exploration.

## 5. Merge policy

- Deterministic `inconclusive` → judge skipped (quota saved), run excluded from accuracy
  metrics.
- A deterministic hard process failure outranks a contradicting semantic `valid` → merged
  `invalid`/`partial`, flagged for human review.
- **Localization precedence: replay > judge.** A causal replay step is the merged
  `first_error_step`; the judge may only propose an *earlier* reasoning-level step (e.g., the
  misdiagnosis that led to the fatal command), recorded alongside the causal step, never
  instead of it. Absent replay evidence, the judge's validated citation stands; absent both,
  the merged localization is an honest `unlocatable`.
- `correct_result_invalid_process` derives only from conclusive runs (§3).
- A human adjudication overrides aggregate labels but never modifies or deletes the stored
  evaluator result.

## 6. Metrics and validation protocol

**Campaign metrics** (single pre-registered pass, slice × configs × 1 attempt): per config —
resolve rate and process-validity rate (predicted and adjudicated, both labeled); overall —
final-answer accuracy, process correctness rate, resolved-but-invalid rate, error-type
distribution, per-difficulty and per-category breakdown with the capability boundary described.
No error bars claimed; single-attempt scope stated honestly.

**Evaluator validation** (every number with explicit numerator, denominator, exclusions, and
label provenance):

1. **Localization accuracy** — blinded human first-error labels on every gradeable failed run
   — or, above ~25 of them, on a pre-registered seeded subset (sabotage-style fixtures
   backfill if too few) — captured before any evaluator output is
   revealed; exact-step and ±1-step agreement, reported as a **three-way agreement analysis**
   (replay × judge × human) so localization never rests on the LLM's word alone.
2. **False-positive rate** — every resolved run flagged process-invalid is human-audited:
   real problem vs. false alarm.
3. **Discriminative validation** — the valid / invalid / inconclusive fixture tiers must come
   out correctly ranked.
4. **Consistency** — the ten judge-stability sessions below, plus **one additional judge
   session per campaign run** (Day 7): verdict and first-error agreement reported across the
   whole campaign. The first session remains the official evaluation (decision 12 carve-out);
   the repeats live under `results/judge-stability/`. First cut if the schedule slips.

**Gate:** the judge must reproduce the fixture oracles (valid → zero findings; invalid → known
first-error step and category) before any campaign quota is spent.

**Pre-registration (decision 15).** One committed file freezes, before the first campaign call:
the task list, configuration list, run order, the substitution rule (decision 12's
infrastructure exception, verbatim), the quota plan, and this blinding protocol — alongside the
committed Day 1 gate records.

**Blinding enforcement (decision 17).** The evaluation script suppresses verdicts by default
(printing one requires an explicit `--show-verdict`); the annotation CLI records each initial
label with a timestamp before any reveal; reviews are append-only versions; any non-blinded
review is marked as such and excluded from validation metrics by construction.

**Judge stability (bounded; decision 12 carve-out).** Five repeated judge sessions on the
invalid fixture (Day 5, part of the gate) and five on one real flagged campaign run (Day 7).
Per-session verdict / first-error step / category agreement is reported under
`results/judge-stability/`. This is the evidence that the fixed single-judge,
one-call-per-trajectory design is defensible.

**Evaluator v2 and the regression card (decision 16).** Day 7's measured failure modes drive at
most one versioned evaluator revision. The regression card re-evaluates the stored campaign
bundles under v2 against the frozen human labels — deterministic and replay lanes re-run free;
judge re-calls scoped to runs where the semantic lane was load-bearing — and reports detection,
false positives, and exact/±1 localization before and after, under `results/regression/`.
Stored campaign evaluations are never modified. If v1 measures clean, the card records that as
the final result; the loop is self-scoping.

**Provenance.** Every exported metric row carries provenance — `official` (verifier),
`evaluator` (deterministic/replay/semantic), `human` (labels/adjudication), or `mixed` — plus
numerator, denominator, and exclusion list. An empty denominator exports `null`, never a
fabricated zero.
