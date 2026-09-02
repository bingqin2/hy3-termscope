import data from "../data/failure_patterns.json";
import type { FailurePatternsData, Severity } from "../types";
import { Dot, SEVERITY_DOT, Section, Tip } from "./ui";

const fp = data as FailurePatternsData;
const max = Math.max(...fp.rows.map((r) => r.count));

const BAR: Record<Severity, string> = {
  critical: "bg-bad",
  high: "bg-warn",
  medium: "bg-sev-medium",
};

export function FailurePatterns() {
  return (
    <Section
      id="failure-patterns"
      num="03"
      title="Failure patterns"
      blurb="Occurrences of each error type across all runs, from merged deterministic + judge findings. Color encodes the taxonomy's severity tier; the ranking is by incidence."
    >
      <div className="space-y-2">
        {fp.rows.map((r) => (
          <div key={r.error_type} className="flex items-center gap-4">
            <span className="w-56 shrink-0 truncate text-right text-sm text-ink-muted">
              {r.label}
            </span>
            <div className="flex-1">
              <Tip tip={`${r.label} · ${r.count} occurrences · severity ${r.severity}`}>
                <span className="block h-2.5 w-full">
                  <span
                    className={`block h-2.5 rounded-r-[4px] ${BAR[r.severity]}`}
                    style={{ width: `${(r.count / max) * 100}%` }}
                  />
                </span>
              </Tip>
            </div>
            <span className="w-6 shrink-0 text-right font-mono text-xs tabular-nums text-ink">
              {r.count}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-5 flex gap-5 font-mono text-xs text-ink-muted">
        {(["critical", "high", "medium"] as Severity[]).map((s) => (
          <span key={s} className="inline-flex items-center gap-2">
            <Dot className={SEVERITY_DOT[s]} /> {s}
          </span>
        ))}
      </div>
    </Section>
  );
}
