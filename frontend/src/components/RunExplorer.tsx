import { useMemo, useState } from "react";
import data from "../data/runs.json";
import type { Run, RunsData } from "../types";
import { ConfigLabel, DifficultyChip, ProcessChip, Section } from "./ui";

const rd = data as unknown as RunsData;

/** The step the site walks a visitor to: the blinded reference label's first
 *  error on failed runs (the merged evaluator location, where it exists, is
 *  shown as its own marker). */
function referenceStep(run: Run): number | null {
  const fe = run.reference_review?.label.first_error;
  return fe && fe.location === "located" ? fe.step_id : null;
}

function OutcomeChip({ run }: { run: Run }) {
  const style =
    run.outcome === "resolved" ? "border-good/50 text-good" : "border-bad/50 text-bad";
  return (
    <span className={`rounded-full border px-2 py-0.5 font-mono text-[11px] ${style}`}>
      {run.outcome}
    </span>
  );
}

function StepCard({
  run,
  step,
  expanded,
  onToggle,
}: {
  run: Run;
  step: Run["steps"][number];
  expanded: boolean;
  onToggle: () => void;
}) {
  const refStep = referenceStep(run);
  const isRefError = refStep === step.step_id;
  const isMergedError = run.first_error_step === step.step_id;
  const errorType = run.reference_review?.label.error_type;
  const firstLine = (step.command ?? step.content ?? "").split("\n")[0].trim() || step.source;
  return (
    <li className="relative pl-10">
      <span
        className={`absolute left-0 top-0 grid h-6 w-6 place-items-center rounded-full border font-mono text-[11px] ${
          isRefError ? "border-bad bg-bad/15 text-bad" : "border-line bg-surface text-ink-faint"
        }`}
      >
        {step.step_id}
      </span>
      <div
        className={`rounded border ${
          isRefError ? "border-bad/60 bg-bad/10" : "border-line bg-surface"
        }`}
      >
        <button
          onClick={onToggle}
          aria-expanded={expanded}
          className="flex w-full items-center gap-2 px-3 py-2 text-left"
        >
          {isRefError && (
            <span className="shrink-0 font-mono text-[11px] font-bold text-bad">▲</span>
          )}
          {isMergedError && (
            <span className="shrink-0 font-mono text-[11px] font-bold text-warn">◆</span>
          )}
          <span className="min-w-0 flex-1 truncate font-mono text-xs text-ink-muted">
            {step.command ? (
              <>
                <span className="select-none text-ink-faint">$ </span>
                {firstLine}
              </>
            ) : (
              <span className="italic">{firstLine}</span>
            )}
          </span>
          <span className="shrink-0 font-mono text-xs text-ink-faint">{expanded ? "−" : "+"}</span>
        </button>
        {expanded && (
          <div className="border-t border-line/60 px-3 pb-3 pt-2.5">
            {isRefError && (
              <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-wider text-bad">
                ▲ first error · {errorType ?? "uncategorized"} · blinded reference label
              </p>
            )}
            {isMergedError && (
              <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-wider text-warn">
                ◆ evaluator's merged first error{run.replay?.step === step.step_id ? " · causal replay flip" : ""}
              </p>
            )}
            {step.source !== "agent" && (
              <p className="mb-1 font-mono text-[11px] uppercase tracking-wider text-ink-faint">
                {step.source}
              </p>
            )}
            {step.content && (
              <p className="whitespace-pre-wrap text-sm italic leading-relaxed text-ink-muted">
                {step.content}
              </p>
            )}
            {step.command && (
              <pre className="mt-2 overflow-x-auto rounded bg-surface-2 px-3 py-2 font-mono text-[13px] text-ink">
                <span className="select-none text-ink-faint">$ </span>
                {step.command}
              </pre>
            )}
            {step.observation && (
              <pre className="mt-1.5 max-h-56 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-ink-faint">
                {step.observation}
              </pre>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

function RunButton({ run, selected, onSelect }: { run: Run; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full rounded border px-3 py-2.5 text-left transition-colors ${
        selected ? "border-accent/60 bg-surface" : "border-line bg-transparent hover:bg-surface"
      }`}
    >
      <p className="text-sm">{run.task_id}</p>
      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-ink-muted">
        <ConfigLabel id={run.config_id} />
        <span className="font-mono text-[11px] text-ink-faint">{run.difficulty}</span>
        <span className={run.outcome === "resolved" ? "text-good" : "text-bad"}>
          {run.outcome === "resolved" ? "✓" : "✗"}
        </span>
      </div>
    </button>
  );
}

export function RunExplorer() {
  const [showAll, setShowAll] = useState(false);
  // The data file is ordered failed-first (the site's walk order). In "all
  // runs" mode re-sort by task so resolved and failed runs interleave —
  // otherwise the visible top of the list is the same 14 failed runs.
  const runs = useMemo(() => {
    const list = rd.runs.filter((r) => showAll || r.outcome === "unresolved");
    return showAll
      ? [...list].sort(
          (a, b) =>
            a.task_id.localeCompare(b.task_id) || a.config_id.localeCompare(b.config_id),
        )
      : list;
  }, [showAll]);
  const [selected, setSelected] = useState(rd.runs[0].run_id);
  // If the selected run is filtered out (a resolved run while showing failed
  // only), fall back to the first run of the current list.
  const run = runs.find((r) => r.run_id === selected) ?? runs[0];
  const ref = run.reference_review;
  const truncated = run.steps.some((s) => s.observation.length >= 1500);

  // Steps start collapsed except the labeled error steps; the override is
  // keyed to the run so switching runs returns to that default.
  const defaultOpen = useMemo(() => {
    const s = new Set<number>();
    const refStep = referenceStep(run);
    if (refStep != null) s.add(refStep);
    if (run.first_error_step != null) s.add(run.first_error_step);
    return s;
  }, [run]);
  const [openOverride, setOpenOverride] = useState<{ runId: string; open: Set<number> } | null>(
    null,
  );
  const open = openOverride?.runId === run.run_id ? openOverride.open : defaultOpen;
  const setOpen = (next: Set<number>) => setOpenOverride({ runId: run.run_id, open: next });
  const toggleStep = (id: number) => {
    const next = new Set(open);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setOpen(next);
  };

  return (
    <Section
      id="run-explorer"
      num="05"
      title="Run explorer"
      blurb="Walk any stored trajectory to its first error. Steps are collapsed to their first command line — the labeled error steps start expanded; click any step to open it. The red ▲ marker is the blinded reference label; the orange ◆ marker is the evaluator's merged localization (a causal prefix-replay flip where one exists). Every verdict chip carries its provenance."
    >
      <div className="mb-4 flex gap-2 font-mono text-xs">
        <button
          onClick={() => setShowAll(false)}
          className={`rounded-full border px-3 py-1 ${!showAll ? "border-accent/60 text-ink" : "border-line text-ink-muted"}`}
        >
          failed runs ({rd.runs.filter((r) => r.outcome === "unresolved").length})
        </button>
        <button
          onClick={() => setShowAll(true)}
          className={`rounded-full border px-3 py-1 ${showAll ? "border-accent/60 text-ink" : "border-line text-ink-muted"}`}
        >
          all runs ({rd.runs.length})
        </button>
      </div>
      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <div className="max-h-[720px] min-w-0 space-y-2 overflow-y-auto pr-1">
          {runs.map((r) => (
            <RunButton
              key={r.run_id}
              run={r}
              selected={r.run_id === run.run_id}
              onSelect={() => setSelected(r.run_id)}
            />
          ))}
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="mr-2 font-display text-xl font-semibold">{run.task_id}</h3>
            <DifficultyChip difficulty={run.difficulty} />
            <OutcomeChip run={run} />
            <ProcessChip process={run.process} provenance={run.process_provenance} />
            {run.replay && (
              <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[11px] text-ink-muted">
                replay {run.replay.localization}
                {run.replay.step != null ? ` @ ${run.replay.step}` : ""}
              </span>
            )}
            {run.judge_status && run.judge_status !== "ok" && (
              <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[11px] text-ink-faint">
                judge {run.judge_status}
              </span>
            )}
          </div>

          {ref && (
            <div className="mt-4 rounded border-l-2 border-bad bg-surface p-4">
              <p className="font-mono text-[11px] uppercase tracking-wider text-ink-faint">
                {ref.provenance === "human" ? "human adjudication" : "blinded reference label"} ·{" "}
                {ref.reviewer}
                {ref.blinded ? " · captured before any evaluator output" : ""}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{ref.notes}</p>
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-ink-faint">
            <span>{run.steps.length} steps · labeled error steps start expanded</span>
            <button
              onClick={() => setOpen(new Set(run.steps.map((s) => s.step_id)))}
              className="underline decoration-line underline-offset-2 hover:text-ink"
            >
              expand all
            </button>
            <button
              onClick={() => setOpen(new Set())}
              className="underline decoration-line underline-offset-2 hover:text-ink"
            >
              collapse all
            </button>
          </div>
          <ol className="mt-3 space-y-3">
            {run.steps.map((s) => (
              <StepCard
                key={s.step_id}
                run={run}
                step={s}
                expanded={open.has(s.step_id)}
                onToggle={() => toggleStep(s.step_id)}
              />
            ))}
          </ol>
          {truncated && (
            <p className="mt-2 font-mono text-[11px] text-ink-faint">
              long observations are shown truncated to 1,500 characters; the full trajectories live
              in the repository's per-run bundles
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            {run.checks.map((c) => (
              <span
                key={c.name}
                className={`rounded border px-2 py-1 font-mono text-[11px] ${
                  c.status === "passed" ? "border-good/40 text-good" : "border-bad/40 text-bad"
                }`}
              >
                {c.status === "passed" ? "✓" : "✗"} {c.name}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}
