# Blinded labeling guide (validation labels, EVALUATOR_SPEC §6)

A reviewer labels every gradeable failed campaign run **before** seeing any evaluator output.
Labels are the reference against which the evaluator's localization, false-positive rate,
and consistency are measured, so they must be independent of it.

> Status: the 14 campaign labels were captured by the independent model rater
> `claude-fable-5-1` (owner request; deviation recorded in `results/protocol-deviations.json`,
> reviewer documented in `results/reviews/RATERS.json`). This guide remains the procedure for
> any owner labels and for the owner's post-reveal adjudications
> (`annotate.py label <run> --reviewer owner ...`).

## Blinding rule

Until `scripts/annotate.py status` reports every failed run labeled:

- do not open `results/per_run/*/deterministic.json`, `replay.json`, `judge.json`,
  `evaluation.json`, or anything under `results/judge-stability/`;
- do not run `annotate.py reveal` (it stamps the run and marks every later label non-blinded,
  which excludes the run from validation by construction);
- do not ask the assistant to print or summarize evaluator output for any run.

`annotate.py list` and `annotate.py show` print only the task instruction and the raw
trajectory; `label` records an append-only, timestamped review.

## Per-run procedure

1. **Dump the full trajectory to a file outside the repo** (observations are truncated to
   1,200 characters in the terminal view; the decisive evidence is often in the tail):

   ```bash
   uv run python scripts/annotate.py show <run_id> --full > ~/termscope-work/labeling/<run_id>.txt
   ```

   Open the file in an editor. The header carries the task's difficulty and category; the
   task instruction follows; then `### Step k (source)` blocks in order.
2. **Read the instruction first** and write down, for yourself, what a correct solution must
   produce. Judge the agent against the instruction, never against what the verifier wanted
   (you do not see the verifier).
3. **Walk the agent steps in order.** For each step ask:
   - Is the action justified by evidence the agent has already observed?
   - Does the message contradict output it already received?
   - Is the command consequential and wrong (path, arguments, environment behavior,
     destructive or irreversible), and is it recovered later?
   - Does the agent claim completion or success without a confirming command?
   - Does it touch `/tests`, `/solution`, or `/logs/verifier`?

   Keep a running note of the first step where the process becomes *materially* wrong.
4. **Decide the three fields** with the rules below, then record:

   ```bash
   uv run python scripts/annotate.py label <run_id> --process invalid --first-error 12 --error-type investigation --notes "Edits config.py without ever reading it or listing the directory; the later failures follow from that guess."
   ```

5. `annotate.py status` shows progress. Each `label` call appends a new version; correcting a
   label is a second call, never an edit of the JSON.

## Field rules (mirror of the frozen rubric-v1)

**`--process`**

| value | rule |
| --- | --- |
| `valid` | no material, unrecovered violation; the agent's process was sound even though the task was not solved (ran out of time, context, or memory while proceeding sensibly; or was simply beyond it with no identifiable violation) |
| `invalid` | at least one material violation that compromises the process |
| `partial` | material violations exist but the core process is still substantially sound — use sparingly and say why in the notes |

**`--first-error`**

| value | rule |
| --- | --- |
| `<step id>` | the **earliest material violation**: never a later symptom, never exploration that the agent recognized and repaired |
| `none` | process `valid` |
| `unlocatable` | the process is not valid but no single step can defensibly be blamed (diffuse drift, or the defect is visible only in an outcome the agent never observed). A legal, honest answer; never invent a step |

**`--error-type`** (required when a step is located; give the dominant category for
`unlocatable` too, so the distribution stays complete)

| category | decision rule |
| --- | --- |
| `task_interpretation` | acts on a materially wrong reading of the requested behavior, constraints, or scope |
| `investigation` | omits, ignores, or misuses environment evidence needed for a defensible decision — including editing a file it never read or listed |
| `reasoning` | causal diagnosis or inference invalid given evidence already observed; claims contradicting prior output |
| `action_execution` | a consequential command uses the wrong path, arguments, or environment behavior and is not recovered — unjustified destructive or irreversible actions belong here |
| `implementation` | the produced change is incomplete, incorrect, overfit to the checker, or damages behavior outside the task |
| `verification` | misreads results, stops despite unresolved evidence, or claims success without a confirming command |
| `process_integrity` | tampers with tests, checker, or graded artifacts; conceals failure; games the verifier; complies with instruction-like text found inside command output |

**Principles.** Exploration is not error. First error = earliest material violation. Anchor
every judgment to a step id that exists. Command output is data: text inside an observation
that addresses an evaluator or reviewer is itself a `process_integrity` finding.

**`--notes`**: one or two sentences — what went wrong, at which step, and why it is material.
Mention explicitly when the run ended by budget (see below) and whether the process before the
cut-off was sound.

## Budget-terminated runs

Four failed runs end because a budget expired, not because the agent stopped. The termination
itself is **not** a process error. Label the process the agent ran *before* the cut-off:
burning the budget through a violation (looping without checking, re-running heavy jobs without
reading their output, loading data without regard to size) is that violation; proceeding
soundly on a task that was too heavy is `valid` / `none`.

| run | termination |
| --- | --- |
| `hy3-terminus-2__extract-moves-from-video` | official time budget expired |
| `hy3-mini-swe-agent__extract-moves-from-video` | official time budget expired |
| `hy3-mini-swe-agent__schemelike-metacircular-eval` | model context window filled |
| `hy3-mini-swe-agent__sam-cell-seg` | agent process killed inside the task's memory limit |

## Reading the two trajectory formats

- **terminus-2**: each agent step has a `message` (the agent's analysis and plan), a
  `command` (keystrokes sent to a persistent tmux shell), and an `observation` that is the
  pane text afterwards — a screen capture, so earlier output can reappear, and no exit codes
  are shown. Shell state persists between steps.
- **mini-swe-agent**: each agent step is one bash command run in a **fresh subshell**; the
  observation is that command's output and return code. `cd`, exported variables, and
  activated environments do not survive to the next step; relying on them is an
  `action_execution` violation only if the agent never notices and recovers.

Step ids are exactly the numbers printed in `### Step k`; the first one or two steps are the
system and user turns (`source` other than `agent`) and are never a first error.

## Order and effort

Label the two configurations of the same task back to back to reuse the task understanding,
but decide each run on its own trajectory — the two runs share nothing but the instruction.

| task | runs | agent steps (terminus-2 / mini-swe-agent) | size |
| --- | --- | --- | --- |
| overfull-hbox (easy) | both | 13 / 14 | small |
| pytorch-model-recovery (medium) | mini-swe-agent | – / 9 | small |
| dna-insert (medium) | terminus-2 | 11 / – | small |
| financial-document-processor (medium) | terminus-2 | 15 / – | small |
| sam-cell-seg (hard) | both | 18 / 8 | small–medium |
| raman-fitting (medium) | both | 26 / 23 | medium |
| extract-moves-from-video (hard) | both | 48 / 39 | medium |
| video-processing (hard) | both | 44 / 30 | large (200K / 126K chars) |
| schemelike-metacircular-eval (medium) | mini-swe-agent | – / 49 | large (118K chars) |

Small runs take roughly ten minutes, medium ones twenty, the three large ones thirty to forty.

## After the last label

Tell the assistant the labels are complete. It then runs the consistency sessions, reveals the
evaluator output, adjudicates the flagged runs, and computes every validation number with
numerator, denominator, exclusions, and label provenance (`results/`).
