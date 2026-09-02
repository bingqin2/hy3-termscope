import { useState } from "react";
import data from "../data/runs.json";
import type { Run, RunsData } from "../types";
import { ConfigLabel, Section } from "./ui";

const rd = data as RunsData;

function OutcomeChip({ run }: { run: Run }) {
  const style =
    run.outcome === "resolved" ? "border-good/50 text-good" : "border-bad/50 text-bad";
  return (
    <span className={`rounded-full border px-2 py-0.5 font-mono text-[11px] ${style}`}>
      {run.outcome}
    </span>
  );
}

function ProcessChip({ run }: { run: Run }) {
  const style =
    run.process === "valid"
      ? "border-good/50 text-good"
      : run.process === "partial"
        ? "border-warn/50 text-warn"
        : "border-bad/50 text-bad";
  return (
    <span className={`rounded-full border px-2 py-0.5 font-mono text-[11px] ${style}`}>
      process {run.process}
    </span>
  );
}

function StepCard({ run, step }: { run: Run; step: Run["steps"][number] }) {
  const isFirstError = run.first_error_step === step.n;
  return (
    <li className="relative pl-10">
      <span
        className={`absolute left-0 top-0 grid h-6 w-6 place-items-center rounded-full border font-mono text-[11px] ${
          isFirstError ? "border-bad bg-bad/15 text-bad" : "border-line bg-surface text-ink-faint"
        }`}
      >
        {step.n}
      </span>
      <div
        className={`rounded border p-3 ${
          isFirstError ? "border-bad/60 bg-bad/10" : "border-line bg-surface"
        }`}
      >
        {isFirstError && (
          <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-wider text-bad">
            ▲ first error · {run.error_types.join(" · ")}
          </p>
        )}
        <p className="text-sm italic leading-relaxed text-ink-muted">{step.thought}</p>
        <pre className="mt-2 overflow-x-auto rounded bg-surface-2 px-3 py-2 font-mono text-[13px] text-ink">
          <span className="select-none text-ink-faint">$ </span>
          {step.command}
        </pre>
        {step.observation && (
          <pre className="mt-1.5 overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink-faint">
            {step.observation}
          </pre>
        )}
        {step.exit_code !== 0 && (
          <p className="mt-1.5 font-mono text-[11px] text-bad">exit {step.exit_code}</p>
        )}
      </div>
    </li>
  );
}

export function RunExplorer() {
  const [selected, setSelected] = useState(rd.runs[0].run_id);
  const run = rd.runs.find((r) => r.run_id === selected) ?? rd.runs[0];

  return (
    <Section
      id="run-explorer"
      num="05"
      title="Run explorer"
      blurb="Walk any stored trajectory to its evaluation: the step timeline, the localized first error, the judge's evidence-anchored finding, and every verifier check. This is the process evaluation made visible."
    >
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <div className="space-y-2">
          {rd.runs.map((r) => (
            <button
              key={r.run_id}
              onClick={() => setSelected(r.run_id)}
              className={`w-full rounded border px-3 py-2.5 text-left transition-colors ${
                r.run_id === selected
                  ? "border-accent/60 bg-surface"
                  : "border-line bg-transparent hover:bg-surface"
              }`}
            >
              <p className="font-mono text-xs text-ink-faint">{r.run_id}</p>
              <p className="mt-0.5 text-sm">{r.task_name}</p>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-ink-muted">
                <ConfigLabel id={r.config_id} />
              </div>
            </button>
          ))}
        </div>

        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="mr-2 font-display text-xl font-semibold">{run.task_name}</h3>
            <OutcomeChip run={run} />
            <ProcessChip run={run} />
            <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[11px] text-ink-muted">
              score {run.score.toFixed(2)}
            </span>
          </div>

          <ol className="mt-5 space-y-3">
            {run.steps.map((s) => (
              <StepCard key={s.n} run={run} step={s} />
            ))}
          </ol>

          <div className="mt-5 rounded border-l-2 border-accent bg-surface p-4">
            <p className="font-mono text-[11px] uppercase tracking-wider text-ink-faint">
              merged finding
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{run.finding}</p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {run.checks.map((c) => (
              <span
                key={c.id}
                className={`rounded border px-2 py-1 font-mono text-[11px] ${
                  c.pass ? "border-good/40 text-good" : "border-bad/40 text-bad"
                }`}
              >
                {c.pass ? "✓" : "✗"} {c.id}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}
