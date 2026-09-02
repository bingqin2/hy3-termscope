import type { ReactNode } from "react";
import type { ConfigId, Difficulty, Process, Provenance, Severity } from "../types";

/** Fixed categorical assignment — one color per configuration, never cycled. */
export const CONFIG_DOT: Record<ConfigId, string> = {
  "hy3-terminus-2": "bg-cat-a",
  "hy3-mini-swe-agent": "bg-cat-b",
};

export const CONFIG_SHORT: Record<ConfigId, string> = {
  "hy3-terminus-2": "terminus-2",
  "hy3-mini-swe-agent": "mini-swe-agent",
};

export const SEVERITY_DOT: Record<Severity, string> = {
  critical: "bg-bad",
  high: "bg-warn",
  medium: "bg-sev-medium",
};

export const PROCESS_STYLE: Record<Process, string> = {
  valid: "border-good/50 text-good",
  partial: "border-warn/50 text-warn",
  invalid: "border-bad/50 text-bad",
};

export const PROVENANCE_LABEL: Record<Provenance, string> = {
  official: "verifier",
  evaluator: "evaluator",
  human: "human adjudication",
  second_rater: "blinded reference label",
  mixed: "mixed",
};

export function Dot({ className }: { className: string }) {
  return <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${className}`} />;
}

export const DIFF_ORDER: Record<Difficulty, number> = { easy: 1, medium: 2, hard: 3 };

/** Official Terminal-Bench 2.0 difficulty tier, spelled out with a filled-dot scale. */
export function DifficultyChip({ difficulty }: { difficulty: Difficulty }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line px-2 py-0.5 font-mono text-[11px] text-ink-muted">
      <span className="tracking-tighter text-accent">
        {"●".repeat(DIFF_ORDER[difficulty])}
        {"○".repeat(3 - DIFF_ORDER[difficulty])}
      </span>
      {difficulty}
    </span>
  );
}

export function ConfigLabel({ id, long }: { id: ConfigId; long?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Dot className={CONFIG_DOT[id]} />
      <span>{long ?? CONFIG_SHORT[id]}</span>
    </span>
  );
}

export function ProcessChip({
  process,
  provenance,
}: {
  process: Process | null;
  provenance?: Provenance;
}) {
  if (process === null) {
    return (
      <span
        className="rounded-full border border-line px-2 py-0.5 font-mono text-[11px] text-ink-faint"
        title="no semantic verdict (honest null)"
      >
        process n/a
      </span>
    );
  }
  const tip = provenance ? `process label provenance: ${PROVENANCE_LABEL[provenance]}` : undefined;
  return (
    <span
      className={`rounded-full border px-2 py-0.5 font-mono text-[11px] ${PROCESS_STYLE[process]}`}
      title={tip}
    >
      process {process}
      {provenance === "human" ? " ·H" : ""}
    </span>
  );
}

export function Tip({ tip, children }: { tip: string; children: ReactNode }) {
  return (
    <span className="group/tip relative inline-flex w-full">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1.5 hidden -translate-x-1/2 whitespace-nowrap rounded border border-line bg-surface-2 px-2 py-1 font-mono text-[11px] text-ink shadow-lg group-hover/tip:block">
        {tip}
      </span>
    </span>
  );
}

export function Section({
  id,
  num,
  title,
  blurb,
  children,
}: {
  id: string;
  num: string;
  title: string;
  blurb?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="border-t border-line">
      <div className="mx-auto max-w-5xl px-6 py-16">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-sm font-medium text-accent">{num}</span>
          <h2 className="font-display text-3xl font-semibold tracking-tight">{title}</h2>
        </div>
        {blurb && <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-muted">{blurb}</p>}
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}

export const th =
  "px-3 py-2 text-left font-mono text-[11px] font-medium uppercase tracking-wider text-ink-faint";
export const td = "px-3 py-3 text-sm";
