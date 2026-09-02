# Next steps

Current step: **Day 5 — semantic lane & judge gate** (Days 1–4 complete; exit conditions met).

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
