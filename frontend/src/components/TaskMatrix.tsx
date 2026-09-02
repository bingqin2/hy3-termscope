import data from "../data/tasks.json";
import type { ConfigId, TasksData } from "../types";
import { ConfigLabel, Section, Tip, th, td } from "./ui";

const tasks = data as TasksData;
const CONFIGS: ConfigId[] = ["hy3-react", "hy3-react-verify", "hy3-oneshot"];

function Cell({ score, task, config }: { score: number; task: string; config: string }) {
  const kind = score >= 0.995 ? "pass" : score <= 0.005 ? "fail" : "partial";
  const style =
    kind === "pass"
      ? "bg-good/10 text-good"
      : kind === "fail"
        ? "bg-bad/10 text-bad"
        : "bg-warn/10 text-warn";
  const glyph = kind === "pass" ? "✓" : kind === "fail" ? "✗" : score.toFixed(2);
  return (
    <Tip tip={`${task} · ${config} · ${Math.round(score * 100)}% of verifier checks`}>
      <span
        className={`grid h-9 w-full place-items-center rounded-sm font-mono text-[13px] tabular-nums ${style}`}
      >
        {glyph}
      </span>
    </Tip>
  );
}

export function TaskMatrix() {
  return (
    <Section
      id="per-task"
      num="02"
      title="Per-task results"
      blurb="Fractional scores are the weighted share of verifier checks passed — symptom, root cause, durability after restart, side effects, cleanup, data integrity. A full ✓ requires every critical check."
    >
      <div className="overflow-x-auto rounded border border-line">
        <table className="w-full min-w-[640px] border-collapse">
          <thead className="border-b border-line bg-surface">
            <tr>
              <th className={th}>Task</th>
              <th className={th}>Diff.</th>
              {CONFIGS.map((c) => (
                <th key={c} className={`${th} w-28 text-center`}>
                  <ConfigLabel id={c} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tasks.rows.map((t) => (
              <tr key={t.task_id} className="border-b border-line last:border-0 hover:bg-surface">
                <td className={td}>
                  <span className="mr-2 font-mono text-xs text-ink-faint">{t.task_id}</span>
                  {t.name}
                </td>
                <td className={`${td} font-mono text-xs text-ink-muted`}>
                  {"●".repeat(t.difficulty)}
                  {"○".repeat(3 - t.difficulty)}
                </td>
                {CONFIGS.map((c) => (
                  <td key={c} className="px-1.5 py-1.5">
                    <Cell score={t.scores[c]} task={t.name} config={c} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 font-mono text-xs text-ink-faint">
        <span className="text-good">✓</span> all critical checks · {" "}
        <span className="text-warn">0.xx</span> fraction of checks · {" "}
        <span className="text-bad">✗</span> no checks
      </p>
    </Section>
  );
}
