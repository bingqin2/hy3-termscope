import meta from "../data/meta.json";
import type { MetaData } from "../types";
import type { PageId } from "../App";

const m = meta as MetaData;

const NAV: readonly [string, string, PageId][] = [
  ["01", "Leaderboard", "leaderboard"],
  ["02", "Tasks", "per-task"],
  ["03", "Failures", "failure-patterns"],
  ["04", "Taxonomy", "taxonomy"],
  ["05", "Runs", "run-explorer"],
  ["06", "Validation", "validation"],
];

export function Header({ active }: { active: PageId }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-ground/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-1 px-6 py-3">
        <a href="#leaderboard" className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center rounded-sm bg-accent font-mono text-[11px] font-bold text-ground">
            TS
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">TermScope</span>
        </a>
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {NAV.map(([num, label, id]) => (
            <a
              key={id}
              href={`#${id}`}
              aria-current={active === id ? "page" : undefined}
              className={`font-mono text-xs transition-colors hover:text-ink ${
                active === id
                  ? "rounded-full border border-accent/50 bg-surface px-2.5 py-0.5 text-ink"
                  : "text-ink-muted"
              }`}
            >
              <span className="text-accent">{num}</span> {label}
            </a>
          ))}
        </nav>
        <a
          href="https://github.com/bingqin2/hy3-termscope"
          target="_blank"
          rel="noreferrer"
          className="ml-auto font-mono text-xs text-ink-muted transition-colors hover:text-ink"
        >
          GitHub ↗
        </a>
      </div>
    </header>
  );
}

export function Hero() {
  const tokens =
    m.agent_tokens_total != null ? `${(m.agent_tokens_total / 1e6).toFixed(1)}M agent tokens` : "";
  return (
    <div id="top" className="mx-auto max-w-5xl px-6 pb-14 pt-20">
      <h1 className="font-display text-5xl font-semibold leading-[1.04] tracking-tight md:text-6xl">
        Process evaluation for terminal agents.
      </h1>
      <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-muted">
        Hy3 drives two agent scaffolds through Terminal-Bench 2.0 tasks; a three-lane evaluator
        judges <em className="text-ink">how</em> — deterministic facts, prefix-replay causal
        localization that re-runs command prefixes in fresh containers, and a blinded LLM judge.
        The evaluator itself is then measured against blinded reference labels, and its failures
        are reported as findings.
      </p>
      <div className="mt-8 flex flex-wrap gap-2 font-mono text-xs text-ink-muted">
        {[
          "Hy3 only · terminus-2 + mini-swe-agent",
          `${m.n_tasks} TB2 tasks · single attempt`,
          `${m.n_runs} runs · ${tokens}`,
          "replay-based localization",
          "blinded validation",
        ].map((c) => (
          <span key={c} className="rounded-full border border-line bg-surface px-3 py-1">
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto max-w-5xl px-6 py-10 text-sm text-ink-muted">
        <p>
          Individual activity work for the 2026 Tencent Rhino-Bird open-source practical task
          (Hunyuan LLM track) — <span className="text-ink">not an official Tencent product</span>.
          Runs{" "}
          <a
            href="https://github.com/laude-institute/terminal-bench"
            target="_blank"
            rel="noreferrer"
            className="text-accent hover:underline"
          >
            Terminal-Bench 2.0
          </a>{" "}
          via the Harbor CLI (Laude Institute); not affiliated with Terminal-Bench.
        </p>
        <p className="mt-3 font-mono text-xs text-ink-faint">
          <a
            href="https://github.com/bingqin2/hy3-termscope"
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink"
          >
            Source
          </a>
          {" · "}
          <a
            href="https://github.com/Tencent-Hunyuan"
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink"
          >
            Hy3
          </a>
          {" · MIT · every number re-derivable from committed results/*.json"}
        </p>
      </div>
    </footer>
  );
}
