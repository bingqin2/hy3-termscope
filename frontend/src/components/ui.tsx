import type { ReactNode } from "react";
import type { ConfigId, Severity } from "../types";

/** Fixed categorical assignment — one color per configuration, never cycled. */
export const CONFIG_DOT: Record<ConfigId, string> = {
  "hy3-react": "bg-cat-a",
  "hy3-react-verify": "bg-cat-b",
  "hy3-oneshot": "bg-cat-c",
};

export const CONFIG_SHORT: Record<ConfigId, string> = {
  "hy3-react": "ReAct",
  "hy3-react-verify": "ReAct+verify",
  "hy3-oneshot": "one-shot",
};

export const SEVERITY_DOT: Record<Severity, string> = {
  critical: "bg-bad",
  high: "bg-warn",
  medium: "bg-sev-medium",
};

export function Dot({ className }: { className: string }) {
  return <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${className}`} />;
}

export function ConfigLabel({ id, long }: { id: ConfigId; long?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Dot className={CONFIG_DOT[id]} />
      <span>{long ?? CONFIG_SHORT[id]}</span>
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
