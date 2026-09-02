import data from "../data/failure_patterns.json";
import type { FailurePatternsData, Severity } from "../types";
import { Dot, SEVERITY_DOT, Section, Tip } from "./ui";

const fp = data as unknown as FailurePatternsData;
const max = Math.max(1, ...fp.rows.map((r) => r.count));

const BAR: Record<Severity, string> = {
  critical: "bg-bad",
  high: "bg-warn",
  medium: "bg-sev-medium",
};

export function FailurePatterns() {
  const rows = [...fp.rows].sort((a, b) => b.count - a.count);
  return (
    <Section
      id="failure-patterns"
      num="03"
      title="Failure patterns"
      blurb="Primary error category at the first error of each failed run, from the blinded reference labels (owner adjudication overrides where present). Hy3's dominant failure on this slice is reasoning: committing to a wrong interpretation of the evidence and never re-examining it — not destructive commands."
    >
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.error_type} className="flex items-center gap-4">
            <span className="w-56 shrink-0 truncate text-right text-sm text-ink-muted">
              {r.label}
            </span>
            <div className="flex-1">
              <Tip
                tip={`${r.label} · ${r.count} failed runs (terminus-2 ${r.by_config["hy3-terminus-2"]}, mini-swe-agent ${r.by_config["hy3-mini-swe-agent"]}) · severity ${r.severity}`}
              >
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
      <div className="mt-5 flex flex-wrap items-center gap-5 font-mono text-xs text-ink-muted">
        {(["critical", "high", "medium"] as Severity[]).map((s) => (
          <span key={s} className="inline-flex items-center gap-2">
            <Dot className={SEVERITY_DOT[s]} /> {s}
          </span>
        ))}
        <span className="text-ink-faint">
          provenance: blinded reference labels · 12 located first errors across 14 failed runs
        </span>
      </div>
    </Section>
  );
}
