import data from "../data/validation.json";
import type { Ratio, ValidationData } from "../types";
import { Section, th, td } from "./ui";

const v = data as unknown as ValidationData;

function ratio(r: Ratio, na = "n/a"): string {
  return r.num == null || r.den == null ? na : `${r.num}/${r.den}`;
}

function Tile({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div className="rounded border border-line bg-surface p-5">
      <p className="font-mono text-3xl font-medium tabular-nums">{value}</p>
      <p className="mt-2 font-mono text-[11px] uppercase tracking-wider text-ink-faint">{label}</p>
      <p className="mt-1 text-xs leading-relaxed text-ink-muted">{sub}</p>
    </div>
  );
}

const REG_ROWS = [
  ["Detection of non-valid processes", "detection_nonvalid"],
  ["Verdict agreement (3-way)", "verdict_agreement_3way"],
  ["Localization · exact", "localization_exact"],
  ["Localization · reference-located only", "localization_located_only"],
  ["Category agreement at the exact step", "category_agreement_at_exact_step"],
] as const;

export function Validation() {
  const m = v.regression.metrics;
  return (
    <Section
      id="validation"
      num="06"
      title="Method & validation"
      blurb="The evaluator is measured, not trusted: blinded reference labels on every failed run (captured before any evaluator output existed for the labeler), fixture gates, repeat-session consistency, and a versioned revision scored on a regression card. Honest nulls stay null, and the evaluator's own failure is reported as a finding."
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile
          value={ratio(v.localization_exact)}
          label="Localization · exact"
          sub="merged first error equals the blinded reference label (same step, or both honestly 'none')"
        />
        <Tile
          value={ratio(v.localization_located_only)}
          label="Localization · located refs only"
          sub="exact step match on the 12 runs whose reference label pins a step — the hard cases"
        />
        <Tile
          value={ratio(v.false_positive_rate, "0 flagged")}
          label="False-positive audit"
          sub="resolved runs flagged process-invalid: none were flagged, so the denominator is honestly empty"
        />
        <Tile
          value={v.consistency.verdict_agreement}
          label="Judge self-consistency"
          sub={`repeat sessions across the campaign (flagged-run stability ${
            v.consistency.flagged_run_stability?.verdict ?? "—"
          }): temperature-0 verdicts are stable — the errors are systematic, not noise`}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="min-w-0">
          <h3 className="font-display text-xl font-semibold">The negative result</h3>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">
            The blinded reference labels rate 12 of 14 failed runs partial or invalid, yet the Hy3
            judge returned <span className="font-mono">valid</span> on every completed campaign
            call — while reproducing the sabotage fixture perfectly and agreeing with itself
            almost perfectly across repeats. A hardened rubric (v2, with four mandatory audits
            the validator enforces and a far wider evidence window) did not fix it: the audits
            get filled, the decisive commitment gets named, and the verdict still absolves. The
            card records this <em className="text-ink">audit-then-absolve</em> mode as measured
            self-evaluation bias — Hy3 judging Hy3 inside the agent's own frame. Localization
            credibility therefore rests on the deterministic and causal-replay lanes plus the
            blinded labels, and the one causal replay flip matches the reference label exactly.
          </p>
          <p className="mt-3 font-mono text-xs leading-relaxed text-ink-faint">
            fixture gates: v1 {v.fixture_gate_v1.split(" (")[0]} · v2{" "}
            {v.regression.fixture_gate_v2?.passed ? "passed" : "failed"} — the anti-leniency
            revision keeps the valid fixture valid with zero findings · reference labels:{" "}
            {v.reference_labels?.second_rater ?? 0} blinded second-rater,{" "}
            {v.reference_labels?.human ?? 0} human
          </p>
        </div>
        <div className="min-w-0 overflow-x-auto rounded border border-line">
          <table className="w-full min-w-[380px] border-collapse">
            <thead className="border-b border-line bg-surface">
              <tr>
                <th className={th}>Regression card vs frozen labels</th>
                <th className={`${th} text-right`}>evaluator v1</th>
                <th className={`${th} text-right`}>evaluator v2</th>
              </tr>
            </thead>
            <tbody>
              {REG_ROWS.map(([label, key]) => (
                <tr key={key} className="border-b border-line last:border-0">
                  <td className={`${td} text-ink-muted`}>{label}</td>
                  <td className={`${td} text-right font-mono tabular-nums`}>{m[key].v1}</td>
                  <td className={`${td} text-right font-mono tabular-nums`}>{m[key].v2}</td>
                </tr>
              ))}
              <tr>
                <td className={`${td} text-ink-muted`}>Resolved runs flagged invalid</td>
                <td className={`${td} text-right font-mono tabular-nums`}>
                  {m.resolved_flagged_invalid.v1.length}
                </td>
                <td className={`${td} text-right font-mono tabular-nums`}>
                  {m.resolved_flagged_invalid.v2.length}
                </td>
              </tr>
            </tbody>
          </table>
          <p className="px-3 py-2 font-mono text-[11px] leading-relaxed text-ink-faint">
            v2's one detection gain comes from the merge policy (a causal replay flip now caps a
            contradicting semantic "valid" at "partial"), not from the judge. Stored campaign
            evaluations remain official v1; the loop closed at one revision by pre-registration.
          </p>
        </div>
      </div>

      <p className="mt-6 max-w-3xl font-mono text-xs leading-relaxed text-ink-faint">
        protocol: pre-registered slice and run order, single attempt per pair · deterministic
        facts and prefix-replay run without model calls · judge blinded to the verifier outcome ·
        labels appended-only and timestamped before any reveal · every exported number carries
        numerator, denominator, and provenance, re-derivable from committed results/*.json
      </p>
    </Section>
  );
}
