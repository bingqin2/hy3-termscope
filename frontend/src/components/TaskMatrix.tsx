import data from "../data/tasks.json";
import type { ConfigId, Difficulty, TaskCell, TasksData } from "../types";
import { CONFIG_SHORT, ConfigLabel, PROVENANCE_LABEL, Section, Tip, th, td } from "./ui";

const tasks = data as unknown as TasksData;
const CONFIGS: ConfigId[] = ["hy3-terminus-2", "hy3-mini-swe-agent"];

const DIFF_ORDER: Record<Difficulty, number> = { easy: 1, medium: 2, hard: 3 };

function Cell({ cell, task, config }: { cell: TaskCell | null; task: string; config: ConfigId }) {
  if (cell === null) {
    return <span className="grid h-9 w-full place-items-center text-ink-faint">·</span>;
  }
  const ok = cell.outcome === "resolved";
  const style = ok ? "bg-good/10 text-good" : "bg-bad/10 text-bad";
  const proc =
    cell.process === null ? "–" : cell.process === "valid" ? "V" : cell.process === "partial" ? "P" : "I";
  const procStyle =
    cell.process === "valid"
      ? "text-good"
      : cell.process === "partial"
        ? "text-warn"
        : cell.process === "invalid"
          ? "text-bad"
          : "text-ink-faint";
  const tip = `${task} · ${CONFIG_SHORT[config]} · ${cell.outcome} · process ${
    cell.process ?? "n/a"
  } (${PROVENANCE_LABEL[cell.process_provenance]})`;
  return (
    <Tip tip={tip}>
      <span
        className={`grid h-9 w-full grid-cols-[1fr_auto] items-center rounded-sm px-2 font-mono text-[13px] ${style}`}
      >
        <span>{ok ? "✓" : "✗"}</span>
        <span className={`text-[11px] ${procStyle}`}>{proc}</span>
      </span>
    </Tip>
  );
}

export function TaskMatrix() {
  const rows = [...tasks.rows].sort(
    (a, b) => DIFF_ORDER[a.difficulty] - DIFF_ORDER[b.difficulty] || a.name.localeCompare(b.name),
  );
  return (
    <Section
      id="per-task"
      num="02"
      title="Per-task results"
      blurb="Outcome (✓ resolved / ✗ unresolved) is the official Terminal-Bench verifier reward; the small letter is the adjudicated process verdict — V valid, P partial, I invalid, – no semantic verdict (an honest null). Hover a cell for its provenance."
    >
      <div className="overflow-x-auto rounded border border-line">
        <table className="w-full min-w-[680px] border-collapse">
          <thead className="border-b border-line bg-surface">
            <tr>
              <th className={th}>Task</th>
              <th className={th}>Category</th>
              <th className={th}>Diff.</th>
              {CONFIGS.map((c) => (
                <th key={c} className={`${th} w-36 text-center`}>
                  <ConfigLabel id={c} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.task_id} className="border-b border-line last:border-0 hover:bg-surface">
                <td className={td}>{t.name}</td>
                <td className={`${td} font-mono text-xs text-ink-muted`}>{t.category}</td>
                <td className={`${td} font-mono text-xs text-ink-muted`}>
                  {"●".repeat(DIFF_ORDER[t.difficulty])}
                  {"○".repeat(3 - DIFF_ORDER[t.difficulty])}
                </td>
                {CONFIGS.map((c) => (
                  <td key={c} className="px-1.5 py-1.5">
                    <Cell cell={t.cells[c]} task={t.name} config={c} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 font-mono text-xs text-ink-faint">
        difficulty ●○○ easy · ●●○ medium · ●●● hard — slice frozen by pre-registration before the
        campaign; identical flags for both configurations
      </p>
    </Section>
  );
}
