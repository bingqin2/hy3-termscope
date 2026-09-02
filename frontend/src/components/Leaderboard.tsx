import data from "../data/leaderboard.json";
import type { LeaderboardData } from "../types";
import { CONFIG_DOT, ConfigLabel, Section, th, td } from "./ui";

const lb = data as LeaderboardData;

export function Leaderboard() {
  return (
    <Section
      id="leaderboard"
      num="01"
      title="Leaderboard"
      blurb={`Updated ${lb.updated}. Mean effective score across 12 tasks — single attempt per (configuration, task) pair under a hard API budget, so no error bars are shown or implied. All configurations are Hy3; the comparison is across agent settings, not models.`}
    >
      <div className="overflow-x-auto rounded border border-line">
        <table className="w-full min-w-[560px] border-collapse">
          <thead className="border-b border-line bg-surface">
            <tr>
              <th className={th}>#</th>
              <th className={th}>Configuration</th>
              <th className={th}>Mean score</th>
              <th className={`${th} text-right`}>Resolve rate</th>
              <th className={`${th} text-right`}>Tasks won</th>
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
                    <span className="font-mono tabular-nums">{r.mean_score.toFixed(2)}</span>
                    <span className="h-1.5 w-28 overflow-hidden rounded-full bg-surface-2">
                      <span
                        className={`block h-full rounded-r-full ${CONFIG_DOT[r.config_id]}`}
                        style={{ width: `${r.mean_score * 100}%` }}
                      />
                    </span>
                  </div>
                </td>
                <td className={`${td} text-right font-mono tabular-nums`}>
                  {Math.round(r.resolve_rate * 100)}%
                </td>
                <td className={`${td} text-right font-mono tabular-nums`}>{r.tasks_won}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
