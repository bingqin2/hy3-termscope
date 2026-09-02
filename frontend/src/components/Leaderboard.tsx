import data from "../data/leaderboard.json";
import tasksData from "../data/tasks.json";
import type { ConfigId, Difficulty, LeaderboardData, TasksData } from "../types";
import { CONFIG_DOT, ConfigLabel, DifficultyChip, Section, Tip, th, td } from "./ui";

const lb = data as unknown as LeaderboardData;
const taskRows = (tasksData as unknown as TasksData).rows;
const TIERS: Difficulty[] = ["easy", "medium", "hard"];

function pct(x: number | null): string {
  return x == null ? "—" : `${Math.round(x * 100)}%`;
}

function tierCell(config: ConfigId, tier: Difficulty): string {
  const rows = taskRows.filter((t) => t.difficulty === tier && t.cells[config] != null);
  const won = rows.filter((t) => t.cells[config]?.outcome === "resolved").length;
  return `${won}/${rows.length}`;
}

const tiersIdentical = TIERS.every(
  (t) => new Set(lb.rows.map((r) => tierCell(r.config_id, t))).size === 1,
);

export function Leaderboard() {
  return (
    <Section
      id="leaderboard"
      num="01"
      title="Leaderboard"
      blurb={`Updated ${lb.updated}. 20 pre-registered Terminal-Bench 2.0 tasks × 2 scaffolds, one attempt per (task, configuration) pair by design — no error bars are shown or implied. Both configurations run the same Hy3 model; the comparison is across scaffolds. Resolve rate is the official verifier outcome; process validity is the share of conclusive runs whose process is valid — as predicted by the evaluator, and as adjudicated with reference labels and human rulings layered on top.`}
    >
      <div className="overflow-x-auto rounded border border-line">
        <table className="w-full min-w-[640px] border-collapse">
          <thead className="border-b border-line bg-surface">
            <tr>
              <th className={th}>#</th>
              <th className={th}>Configuration</th>
              <th className={th}>Resolve rate</th>
              <th className={`${th} text-right`}>Resolved</th>
              <th className={`${th} text-right`}>
                <Tip tip="share of conclusive runs the evaluator's merged verdict calls valid">
                  <span>Process validity · predicted</span>
                </Tip>
              </th>
              <th className={`${th} text-right`}>
                <Tip tip="reference labels + human adjudication override the evaluator where present">
                  <span>Process validity · adjudicated</span>
                </Tip>
              </th>
            </tr>
          </thead>
          <tbody>
            {lb.rows.map((r, i) => (
              <tr key={r.config_id} className="border-b border-line last:border-0 hover:bg-surface">
                <td className={`${td} font-mono text-ink-faint`}>{i + 1}</td>
                <td className={td}>
                  <ConfigLabel id={r.config_id} long={r.label} />
                </td>
                <td className={td}>
                  <div className="flex items-center gap-3">
                    <span className="font-mono tabular-nums">{pct(r.resolve_rate)}</span>
                    <span className="h-1.5 w-28 overflow-hidden rounded-full bg-surface-2">
                      <span
                        className={`block h-full rounded-r-full ${CONFIG_DOT[r.config_id]}`}
                        style={{ width: `${(r.resolve_rate ?? 0) * 100}%` }}
                      />
                    </span>
                  </div>
                </td>
                <td className={`${td} text-right font-mono tabular-nums`}>
                  {r.tasks_won}/{r.n_runs - r.n_inconclusive}
                </td>
                <td className={`${td} text-right font-mono tabular-nums`}>
                  {pct(r.process_validity_rate_predicted)}
                </td>
                <td className={`${td} text-right font-mono tabular-nums`}>
                  {pct(r.process_validity_rate_adjudicated)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-6 overflow-x-auto rounded border border-line">
        <table className="w-full min-w-[480px] border-collapse">
          <thead className="border-b border-line bg-surface">
            <tr>
              <th className={th}>Resolved by difficulty tier</th>
              {TIERS.map((t) => (
                <th key={t} className={`${th} text-right`}>
                  <DifficultyChip difficulty={t} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lb.rows.map((r) => (
              <tr key={r.config_id} className="border-b border-line last:border-0 hover:bg-surface">
                <td className={td}>
                  <ConfigLabel id={r.config_id} />
                </td>
                {TIERS.map((t) => (
                  <td key={t} className={`${td} text-right font-mono tabular-nums`}>
                    {tierCell(r.config_id, t)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {tiersIdentical && (
        <p className="mt-2 font-mono text-xs text-ink-faint">
          the per-tier resolve counts are identical for both configurations — swapping the scaffold
          moved which tasks were solved, not how many at each difficulty
        </p>
      )}
      <p className="mt-3 max-w-3xl font-mono text-xs leading-relaxed text-ink-faint">
        The predicted and adjudicated columns disagree on purpose: the validation section below
        measures the evaluator's semantic lane as too lenient (its verdicts call nearly every
        process valid), while blinded reference labels rate 12 of the 14 failed runs partial or
        invalid. Both numbers are shown with their provenance rather than blending them.
      </p>
    </Section>
  );
}
