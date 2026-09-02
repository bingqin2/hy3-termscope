import { Fragment } from "react";
import data from "../data/tasks.json";
import type { ConfigId, Difficulty, TaskCell, TaskRow, TasksData } from "../types";
import { CONFIG_SHORT, ConfigLabel, DifficultyChip, PROVENANCE_LABEL, Section, Tip, th, td } from "./ui";

const tasks = data as unknown as TasksData;
const CONFIGS: ConfigId[] = ["hy3-terminus-2", "hy3-mini-swe-agent"];
const TIERS: Difficulty[] = ["easy", "medium", "hard"];

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

function resolvedCount(rows: TaskRow[], config: ConfigId): number {
  return rows.filter((r) => r.cells[config]?.outcome === "resolved").length;
}

export function TaskMatrix() {
  const groups = TIERS.map((tier) => ({
    tier,
    rows: tasks.rows
      .filter((r) => r.difficulty === tier)
      .sort((a, b) => a.name.localeCompare(b.name)),
  })).filter((g) => g.rows.length > 0);
  return (
    <Section
      id="per-task"
      num="02"
      title="Per-task results"
      blurb="Tasks are grouped by their official Terminal-Bench 2.0 difficulty tier; each tier header carries the per-configuration resolve count. Outcome (✓ resolved / ✗ unresolved) is the official verifier reward; the small letter is the adjudicated process verdict — V valid, P partial, I invalid, – no semantic verdict (an honest null). Hover a cell for its provenance."
    >
      <div className="overflow-x-auto rounded border border-line">
        <table className="w-full min-w-[640px] border-collapse">
          <thead className="border-b border-line bg-surface">
            <tr>
              <th className={th}>Task</th>
              <th className={th}>Category</th>
              {CONFIGS.map((c) => (
                <th key={c} className={`${th} w-36 text-center`}>
                  <ConfigLabel id={c} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <Fragment key={g.tier}>
                <tr className="border-b border-line bg-surface-2">
                  <td colSpan={2 + CONFIGS.length} className="px-3 py-2 font-mono text-xs">
                    <DifficultyChip difficulty={g.tier} />
                    <span className="text-ink-muted"> · {g.rows.length} tasks</span>
                    {CONFIGS.map((c) => (
                      <span key={c} className="text-ink-muted">
                        {" "}
                        · {CONFIG_SHORT[c]} {resolvedCount(g.rows, c)}/{g.rows.length} resolved
                      </span>
                    ))}
                  </td>
                </tr>
                {g.rows.map((t) => (
                  <tr key={t.task_id} className="border-b border-line last:border-0 hover:bg-surface">
                    <td className={td}>{t.name}</td>
                    <td className={`${td} font-mono text-xs text-ink-muted`}>{t.category}</td>
                    {CONFIGS.map((c) => (
                      <td key={c} className="px-1.5 py-1.5">
                        <Cell cell={t.cells[c]} task={t.name} config={c} />
                      </td>
                    ))}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 font-mono text-xs text-ink-faint">
        difficulty tiers are the official Terminal-Bench 2.0 labels — slice frozen by
        pre-registration before the campaign; identical flags for both configurations
      </p>
    </Section>
  );
}
