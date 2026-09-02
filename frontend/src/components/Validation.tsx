import data from "../data/validation.json";
import type { ValidationData } from "../types";
import { Section } from "./ui";

const v = data as ValidationData;

function Tile({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div className="rounded border border-line bg-surface p-5">
      <p className="font-mono text-3xl font-medium tabular-nums">{value}</p>
      <p className="mt-2 font-mono text-[11px] uppercase tracking-wider text-ink-faint">{label}</p>
      <p className="mt-1 text-xs leading-relaxed text-ink-muted">{sub}</p>
    </div>
  );
}

export function Validation() {
  const exact = v.localization_exact;
  const pm1 = v.localization_pm1;
  const fpr = v.false_positive_rate;
  return (
    <Section
      id="validation"
      num="06"
      title="Method & validation"
      blurb="The evaluator itself is measured, not trusted: blinded human first-error labels on every failed run, a human audit of every resolved run the evaluator flagged, and a gold/sabotage/failed fixture ranking test. Denominators are always shown."
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile
          value={`${Math.round((exact.num / exact.den) * 100)}%`}
          label="Localization · exact step"
          sub={`${exact.num} of ${exact.den} failed runs — judge's first-error step equals the blinded human label`}
        />
        <Tile
          value={`${Math.round((pm1.num / pm1.den) * 100)}%`}
          label="Localization · ±1 step"
          sub={`${pm1.num} of ${pm1.den} failed runs within one step of the human label`}
        />
        <Tile
          value={`${Math.round((fpr.num / fpr.den) * 100)}%`}
          label="False-positive rate"
          sub={`${fpr.num} of ${fpr.den} flagged-but-resolved runs judged a false alarm on human audit`}
        />
        <Tile
          value={v.discriminative.split(" ")[0]}
          label="Discriminative test"
          sub={`${v.discriminative} — gold vs. sabotage vs. failed fixtures ranked in the right order`}
        />
      </div>
      <p className="mt-4 font-mono text-xs text-ink-faint">
        consistency re-judging: {v.consistency} · human labels captured before the judge verdict is
        revealed · deterministic evidence outranks the judge on conflict
      </p>
    </Section>
  );
}
