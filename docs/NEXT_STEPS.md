# Next steps

Current step: **Day 10 — report, audits, demo, freeze** (Day 9 complete; the owner pushes and
enables Pages to put the site live).

## Day 9 status (complete; owner to push + enable Pages)

- **Site data pipeline** (`scripts/build_site_data.py`): derives `frontend/src/data/*.json`
  from committed `results/*.json` + `judge-stability/` + `regression/` (decision 8 — the page
  reads only a frozen snapshot). Failure patterns are re-derived from the blinded reference
  labels with that provenance printed. Every emitted file passes a **publication scan**
  (API-key shapes, env assignments, bearer tokens, local home paths hard-fail the build,
  two-phase so nothing partial is ever written) — trajectory observations can echo container
  environment variables, so this runs before anything becomes public.
- **Frontend relabeled for TB2 and rebuilt on real data** (TermScope branding): leaderboard
  with resolve rate + process validity predicted *and* adjudicated (the 100% vs 68/70%
  disagreement is displayed and explained, not blended); 20-task outcome × process matrix
  with honest-null cells; failure patterns from reference labels; the error taxonomy;
  a run explorer that walks every trajectory with two markers (red = blinded reference label's
  first error with the reviewer's note, orange = evaluator's merged/causal-replay step) and
  provenance on every chip; a validation section with the negative result stated plainly and
  the v1-vs-v2 regression table.
- **Verified in the browser**: all six sections render from real data, zero console errors,
  the default view opens a failed run at its labeled first-error step, mobile horizontal
  overflow fixed (grid min-width blowout) and re-measured at 375 px; production build green
  (gzipped ≈ 420 KB incl. all 40 runs' truncated steps).
- **Pages workflow** (`.github/workflows/deploy.yml`): official actions flow, builds only
  `frontend/` with `VITE_BASE=/<repo>/`, never touches `results/` or credentials.
- **Owner to finish deploy**: push `main`, then GitHub → Settings → Pages → Source = "GitHub
  Actions" (one-time). The repo-name decision (`hy3` vs the working title TermScope) becomes
  sticky at this push — renaming later changes the Pages URL.

Owner items still open from Day 7 (they do not block Day 10):

1. **Owner adjudication** — two runs await the owner:
   `hy3-terminus-2__financial-document-processor` (lane conflict: replay located a causal step,
   judge said valid, reference label agrees with replay) and
   `hy3-terminus-2__schemelike-metacircular-eval` (resolved, honest-null semantic verdict after
   the judge's context_limit). Reveal with
   `uv run python scripts/annotate.py reveal <run> --show-verdict`, then record the ruling with
   `annotate.py label <run> --reviewer owner ...` (it will be non-blinded, which is correct for
   adjudication). Owner may also spot-check any rater label the same way.
2. ~~Consistency sessions~~ — **done**: one repeat judge session per campaign run + five
   stability sessions on the flagged run (`results/judge-stability/`). Verdict agreement
   38/40 (38/39 among completed pairs; the context_limit run reproduced its honest refusal);
   flagged-run stability 5/5. The single genuine disagreement is the flagged run itself: one
   repeat session found partial @ step 12 — the same step replay flipped on and the reference
   label chose — while 6 of 7 sessions on that run said valid. Self-consistency is excellent,
   so the detection gap is a systematic rubric problem, not instrument variance
   (`data/environment-checks/day7-validation.json`). ~44 judge calls, ≈1.2M tokens estimated.

## Day 8 status (complete)

- **Evaluator v2 shipped as the single permitted revision** (decision 16; v1 frozen and
  default): `rubric_v2.md`/`prompt-v2` with four mandatory audits (commitments,
  contradictions, final claim, scope/safety) enforced by the validator, valid-as-earned
  verdict semantics, the externally-terminated-run principle, and a wider fixed observation
  window (6000+3000 chars vs 1600+800); merge-v2 caps a semantic `valid` at `partial` on a
  causal replay flip and adds a category fallback for replay-only localization. Selected via
  `JudgeConfig(version="v2")` / `merge_lanes(..., version="v2")`; 73 tests green.
- **v2 fixture gate passed first try before any campaign re-call**
  (`results/regression/v2-gate.json`): valid fixture stays `valid` with zero findings (the
  anti-leniency revision did not become flag-everything); invalid fixture → `invalid` located
  at the known step with the right category.
- **Regression card built against the frozen blinded labels**
  (`results/regression/regression-card.json`; stored campaign evaluations untouched;
  39 v2 judge calls, 1.43M tokens): detection of non-valid processes 0/12 → 1/12; three-way
  verdict agreement 2/14 → 3/14; localization unchanged (exact 3/14, located-only 1/12); the
  over-limit run stays an honest `context_limit`; v2 flags no resolved run (no new FP-audit
  burden). **The only gain comes from merge-v2's causal-flip cap** — the flagged run now
  merges `partial` at the replay step, matching the reference label.
- **Headline negative result, measured and documented**: all completed v2 judge calls filled
  the mandatory audits (zero validation retries) and still returned `valid` on 13/14 failed
  runs (8 findings across 39 calls). The residual mode is **audit-then-absolve**: the judge
  names the decisive commitment, sometimes even classifies the final check as insufficient,
  then absolves inside the agent's own frame — measured self-evaluation bias (Hy3 judging
  Hy3; EVALUATOR_SPEC §4.8), robust to rubric hardening. Localization credibility therefore
  rests on the replay lane and the blinded reference labels; the semantic lane's limits are
  reported as a finding, not patched further (the decision-16 loop is closed).
- **Metric definitions unified** across the exporter, the regression card, and the validation
  record: exact/±1 counts both-sides-`none` as agreement (3/14), and a stricter located-only
  row (1/12) is reported alongside; the earlier 1/14 cut and its contradictory note are
  corrected in place with a correction note.

## Day 7 status (labels + validation done)

- **Labeling delegated to an independent model rater** (owner request; deviation recorded in
  `results/protocol-deviations.json`, reviewer documented in `results/reviews/RATERS.json`):
  Claude Fable 5.1, one fresh-context session per run, inputs limited to instruction + raw
  trajectory + frozen rubric + termination note; no evaluator output; all **14/14 initial
  labels blinded** (append-only, timestamped before any reveal; reveal markers written when
  the Day 7 analysis later disclosed evaluator output).
- **Label distribution**: process 2 valid / 5 partial / 7 invalid; first error located 12,
  none 2; categories at the first error: reasoning 6, task_interpretation 3,
  implementation 2, action_execution 1.
- **Validation numbers** (full record with denominators and provenance:
  `data/environment-checks/day7-validation.json`; machine-readable: `results/validation.json`):
  merged-vs-reference localization exact 1/14 and ±1 1/14; judge-vs-reference verdict
  agreement 2/14; replay located 1 run and the reference label matches it exactly (step 12);
  false-positive audit honestly null (0 resolved runs flagged); fixture tiers still rank
  correctly. The verdict-agreement gap is partly inflated by an asymmetry (the rater knew the
  run failed; the judge is outcome-blinded) — noted in the record.
- **Measured evaluator-v1 failure modes** (drive the single Day 8 revision, decision 16):
  judge leniency on real trajectories (39/39 completed judge calls said valid; 37/40 zero
  findings), merged `none` overriding semantic localization when replay finds no causal flip,
  and a located step with no category when localization comes from replay alone.
- **Annotation CLI now reviewer-aware** (`scripts/annotate.py`): per-reviewer append-only
  versions under `results/reviews/<run>/<reviewer>/`, `--attach` stores raw rater output,
  reveal markers are per run; exporter (`scripts/export_results.py`) resolves the reference
  label (owner blinded > rater blinded) and adjudication (owner latest > rater blinded >
  evaluator) with per-row provenance; exports now live in `results/` (byte-stable, 40 runs);
  65 tests green.

## Day 6 status (complete)

- **Campaign executed exactly as pre-registered**: 40 runs (20 tasks × 2 configs), single
  attempt each, tasks in slice order, per task `hy3-terminus-2` then `hy3-mini-swe-agent`,
  total concurrency 2 (`scripts/run_campaign.py`); 3.55 h wall-clock; no run left
  inconclusive; no re-run was needed — the decision-12 exception mechanism exists
  (`--rerun KEY --reason`) but stayed unused.
- **Official outcomes**: `hy3-terminus-2` 13/20 resolved, `hy3-mini-swe-agent` 13/20
  resolved (per-difficulty and per-run detail in
  `data/environment-checks/day6-campaign-record.json`).
- **Spend recorded**: agents 21,273,798 tokens (terminus-2 ≈ 420K/run, mini-swe-agent
  ≈ 644K/run; failed heavy runs consumed their time budgets); judge ≈ 1.16M recorded
  (the first 18 calls carry estimated prompt tokens — `results/campaign-incidents.json`).
- **All bundles stored** under `results/per_run/<config>__<task>/` (bundle, deterministic
  facts, judge result, judge usage); 39 judge lanes `ok`, 1 honest `context_limit`
  (prompt larger than the gateway's 192K-token input limit).
- **Every table re-derivable by one script**: `scripts/export_results.py` (byte-stable,
  provenance-tagged, honest nulls; unit-tested). Exports stay in a preview directory outside
  the repo until the Day 7 labels exist.
- **Incidents (4), all classified with evidence** in `results/campaign-incidents.json`:
  judge generation budget (reasoning counted in `max_tokens`), an agent exhausting the
  model's context window, a judge prompt beyond the gateway limit, and an agent process
  SIGKILLed inside its task's official 4 GiB memory limit. Outcome policy now names time,
  memory, and context budgets as agent failures (EVALUATOR_SPEC §3).
- **Replay lane complete** over all 14 failed runs (`scripts/replay_campaign.py`): 33
  probes, none timed out, ~78 s per probe, 44 minutes total, zero model calls. In aggregate
  the lane found one causal destructive step and reported `none` for the other 13 —
  most Hy3 failures on this slice leave the task still completable, so their localization
  rests on the judge's reasoning-level citation (merge precedence, EVALUATOR_SPEC §5).
- **Evaluator-v1 results assembled**: `evaluation.json` for all 40 runs
  (`scripts/assemble_evaluations.py`, immutable; 14 with replay evidence).

## Day 5 status (complete)

- **Semantic lane shipped** (`src/termscope/evaluator/judge.py` + frozen
  `rubric_v1.md`): blinded prompt (task instruction + deterministic-facts summary
  with the verifier outcome deliberately withheld + step-numbered trajectory,
  fixed head+tail observation truncation); Hy3 at temperature 0 in JSON mode;
  local validator cross-references every cited step (dangling citation rejects);
  one schema-repair retry → honest `unavailable`; oversize input → honest
  `context_limit`; raw responses under `.local/judge-raw/`; injection defense in
  the rubric (observations are data; embedded evaluator-directed instructions are
  themselves a reportable finding).
- **Merge policy shipped** (`merge.py`): inconclusive skips the judge; hard
  failures outrank a semantic `valid`; localization precedence replay > judge
  with the judge's earlier reasoning-level step recorded alongside;
  `correct_result_invalid_process` derived only from conclusive runs;
  flag rules for lane conflicts, partials, and resolved-but-invalid.
- **Gate passed first-try, recorded** (`day5-judge-gate.json`): valid fixture →
  `valid`, zero findings, first_error `none`; invalid fixture → `invalid`,
  located step 4, `action_execution` present at the step; **stability 5/5
  verdict, 5/5 first-error step, 4/5 primary category**
  (`results/judge-stability/invalid-fixture-sessions.json`); full-pipeline
  merge demo: replay + judge + facts agree at step 4. Cost: 54,408 tokens over
  7 calls (~7.8K/call — far below the planning average).
- 59 tests green (validator, retry, truncation, blinding, merge precedences all
  unit-covered without API calls).

## Day 4 status (complete 2026-09-01)

- **Replay localizer shipped** (`src/termscope/evaluator/replay.py`): fresh
  container per probe from the task's pinned image; the command prefix 1..k runs
  in one non-interactive shell session; **direct** and **reachability** probes
  (reachability = oracle solution from the prefix state, then checks —
  operationalizing the spec's "reachable outcome"); bisection to the first
  permanent flip, boundary verified, flip probe repeated to catch
  non-determinism; `located / none / unlocatable`; per-probe matrix + runtimes.
- **Exit condition measured and recorded**
  (`data/environment-checks/day4-replay-measurement.json`): invalid fixture →
  **located, step 4 = the known doctored step** (5 probes, 47 s wall); the real
  Day 1 live trial → **`none`** (correct: nothing destroyed; 2 probes, 19 s).
  Probes run ~8–13 s each on fix-git.
- Empirical finding folded back into the design: the real run starts its merge
  inside step 4, so oracle-reachability flips at any mid-merge prefix — the
  fixture's fatal step moved into the pristine read-only window (steps 1–3
  real, `rm -rf .git` at step 4), and the probe-brittleness limitation is now
  stated in EVALUATOR_SPEC §3 with the flip command always recorded in notes.
- 42/42 tests green (flip-search logic covered by pure unit tests with a fake
  prober: locates, none, bad-baseline, non-determinism, probe-failure cases).

## Day 3 status (complete 2026-09-01)

- **Deterministic lane shipped** (`src/termscope/evaluator/deterministic.py`, zero
  model calls): trajectory structure validation; destructive-command,
  failed-streak, and repeated-loop facts; claim-vs-evidence (a final success
  claim needs a confirming non-mutating command after the last mutation);
  write-aware protected-path facts over the pinned surface (`/tests`,
  `/solution`, `/logs/verifier`) — reads recorded but never flagged, writes
  require a recognized write pattern, modify-then-revert emits `transient_edit`,
  unreverted protected writes are the only hard process failures.
- **Exit condition proven in tests (35/35 green)**: valid fixture → `clean`
  (its recovered step-7 `rm -f` is recorded as a fact without flagging);
  invalid fixture → `flagged` with the fatal step in facts (deterministic
  anchor = earliest adverse fact; the causal step is replay's job);
  inconclusive fixture → judge-skip; a read-only reference to `/tests`
  provably does **not** flag; `/app/tests/...` look-alikes don't match.
- Pane-text observations carry no exit codes; "successful write" is
  approximated by the absence of failure indicators and the approximation is
  recorded in the facts' notes whenever exercised.

## Day 2 status (complete 2026-09-01)

- **Slice-v1 frozen**: 20 tasks (easy 3 / medium 11 / hard 6, 14 categories), seeded
  stratified draw (seed 20260902) from the 27 gate passers, full candidate order
  recorded — `data/slices/slice-v1.json`.
- **Pre-registration written**: task list, both configs, config-interleaved run order
  (n-concurrent 2, identical flags), decision-12 substitution rule verbatim, quota
  plan (measured 69K baseline), blinding protocol — `data/slices/preregistration.json`.
  **Owner: commit the slice + pre-registration + gate records to complete the Day 2
  freeze** (decision 15; no new direction after the freeze).
- **Fixtures validate offline**: valid (verbatim live solve) /
  invalid-known-first-error (doctored step 10 `rm -rf .git`, oracle
  action_execution·critical, secondary verification finding at step 11) /
  inconclusive (infrastructure exception, empty verifier) — provenance in
  `data/fixtures/PROVENANCE.md`, validated by `tests/test_fixtures.py` (19/19 green,
  which also caught and fixed the importer's terminus-2 `keystrokes` extraction).

## Owner items

1. **Confirm the submission deadline** — the 10-day sequence + buffer assumes ≈ 2026-09-14.
2. **Disk — verified.** External 2 TB APFS SSD "Elements" (~410 MB/s write verified) hosts
   Docker's disk image (`/Volumes/Elements/Docker`) and `/Volumes/Elements/termscope-local/`
   for raw-state archives and exports; internal disk has 606 GB free; amd64 emulation
   verified (`--platform linux/amd64 alpine` → `x86_64`). Docker needs the SSD attached to
   start; to unplug it, quit Docker Desktop first, then eject "Elements".
3. **Quota — not a constraint (owner-confirmed 2026-09-01).** Per-run token cost is still
   measured at the live trial; keep the account topped up ahead of the Day 6 campaign.
4. **Name decision** — the repo slug `hy3` collides with Tencent's model name. Proposed
   working title: **TermScope** (renaming is cheap until the first push).
5. **`.env`** (already present): `HY3_API_BASE=https://tokenhub.tencentmaas.com/v1`,
   `HY3_AGENT_MODEL=hy3`, `HY3_JUDGE_MODEL=hy3`.
6. **Credentials handoff for Harbor** — create `~/termscope-work/hy3-creds.env` containing
   `OPENAI_API_KEY=<hy3 key>` and `OPENAI_BASE_URL=https://tokenhub.tencentmaas.com/v1`
   (map from `.env`; the file is read only by Harbor, never printed). Powers
   `scripts/run_live_trial.sh`.
7. **macOS Full Disk Access** — grant it to the app running Claude Code (System Settings →
   Privacy & Security) so tooling can read `~/Documents` and the SSD directly.

## Day 1 status

1. ~~Install and pin the Harbor CLI~~ — **done**: harbor 0.22.0 via
   `uv tool install harbor==0.22.0`; versions in
   `data/environment-checks/day1-environment.json`.
2. ~~Oracle-gate candidate TB2 tasks~~ — **done**: seeded 28-task pool
   (`day1-gate-pool.json`, seed 20260901) + seeded 3-task substitution batch;
   **25/28 pool passers + git-multibranch**, all Rosetta (dataset ships amd64-only
   images, pulled prebuilt). Failures recorded: build-cython-ext (oracle fails one
   repo test), qemu-alpine-ssh + qemu-startup (QEMU cannot nest under Rosetta),
   caffe-cifar-10 (oracle exceeds its 1200 s budget under emulation). Full record:
   `data/environment-checks/day1-task-gate.json`.
3. ~~Live Hy3 trial~~ — **done**: `hy3 × terminus-2` (`openai/hy3`) solved `fix-git`
   first try — resolved, reward 1.0, 15 ATIF steps, 1m 59s, **69,401 tokens**
   (61,570 prompt / 45,184 cached / 7,831 completion); imported as hash-verified
   bundle `f4073722…`. Cost sits at the cheap end of the planned 100K–1M range —
   the ~300K/run average and the campaign projection (~16–18M central) stand.
4. ~~Pin trajectory format / artifacts / tamper surface~~ — **done**: ATIF ≤ v1.7
   (per-step token metrics; final_metrics totals); per-trial artifact list and the
   verify-time-only tests upload (agent phase cannot see the checker; container
   network available by default) recorded in `day1-environment.json`.
5. ~~Contracts + importer~~ — **done**: `src/termscope/` pydantic contracts
   (RunBundle, EvaluationResult, HumanReview, findings, checks, replay/judge lanes)
   + ATIF-native importer with content-hash verification; 14 tests green; the
   smoke-trial bundle imports and verifies.

## Exit condition (Day 1)

One Hy3-driven TB2 run imported as a schema-valid, hash-verified bundle; environment-check
records exist for every probed task; trajectory format pinned; per-run token cost measured and
the campaign quota re-estimated. **Met in full (2026-09-01).**
