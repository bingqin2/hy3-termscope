import data from "../data/tasks.json";
import type { TasksData } from "../types";
import { Section, th, td } from "./ui";

const tasks = data as TasksData;

export function Taxonomy() {
  return (
    <Section
      id="taxonomy"
      num="04"
      title="Task taxonomy"
      blurb="12 self-built container incidents across four layers, difficulty-stratified from basic to hard. Every task ships a fault injector, an instruction, and 5–8 executable verifier checks; each also hides a process trap that separates a sound repair from a lucky one."
    >
      <div className="overflow-x-auto rounded border border-line">
        <table className="w-full min-w-[720px] border-collapse">
          <thead className="border-b border-line bg-surface">
            <tr>
              <th className={th}>ID</th>
              <th className={th}>Task</th>
              <th className={th}>Layer</th>
              <th className={th}>Diff.</th>
              <th className={th}>Backend</th>
              <th className={th}>Process trap</th>
            </tr>
          </thead>
          <tbody>
            {tasks.rows.map((t) => (
              <tr key={t.task_id} className="border-b border-line last:border-0 hover:bg-surface">
                <td className={`${td} font-mono text-xs text-ink-faint`}>{t.task_id}</td>
                <td className={td}>{t.name}</td>
                <td className={td}>
                  <span className="rounded-full border border-line bg-surface px-2 py-0.5 font-mono text-[11px] text-ink-muted">
                    {t.layer} · {t.layer_label}
                  </span>
                </td>
                <td className={`${td} font-mono text-xs text-ink-muted`}>
                  {"●".repeat(t.difficulty)}
                  {"○".repeat(3 - t.difficulty)}
                </td>
                <td className={`${td} font-mono text-xs text-ink-muted`}>{t.backend}</td>
                <td className={`${td} text-ink-muted`}>{t.trap}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
