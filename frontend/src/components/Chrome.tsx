const NAV = [
  ["01", "Leaderboard", "#leaderboard"],
  ["02", "Tasks", "#per-task"],
  ["03", "Failures", "#failure-patterns"],
  ["04", "Taxonomy", "#taxonomy"],
  ["05", "Runs", "#run-explorer"],
  ["06", "Validation", "#validation"],
] as const;

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-ground/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-6">
        <a href="#top" className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center rounded-sm bg-accent font-mono text-[11px] font-bold text-ground">
            IS
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">InfraScope</span>
        </a>
        <nav className="hidden items-center gap-4 md:flex">
          {NAV.map(([num, label, href]) => (
            <a
              key={num}
              href={href}
              className="font-mono text-xs text-ink-muted transition-colors hover:text-ink"
            >
              <span className="text-accent">{num}</span> {label}
            </a>
          ))}
        </nav>
        <a
          href="https://github.com/bingqin2/hy3"
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
  return (
    <div id="top" className="mx-auto max-w-5xl px-6 pb-14 pt-20">
      <h1 className="font-display text-5xl font-semibold leading-[1.04] tracking-tight md:text-6xl">
        Process evaluation for infrastructure agents.
      </h1>
      <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-muted">
        A Hy3-powered agent repairs broken infrastructure inside containers; a process-level
        evaluator judges <em className="text-ink">how</em> — first-error localization, an error
        taxonomy, and lifecycle checks that catch fixes which pass the symptom test but leave the
        system unsound.
      </p>
      <div className="mt-8 flex flex-wrap gap-2 font-mono text-xs text-ink-muted">
        {["Hy3-only", "12 tasks · 4 layers", "single-attempt campaign", "MIT"].map((c) => (
          <span key={c} className="rounded-full border border-line bg-surface px-3 py-1">
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}

export function SampleBanner() {
  return (
    <div className="mx-auto max-w-5xl px-6 pb-12">
      <div className="flex items-start gap-3 rounded border border-accent/50 bg-accent/10 px-4 py-3">
        <span className="mt-0.5 font-mono text-xs font-bold uppercase tracking-wider text-accent">
          Sample data
        </span>
        <p className="text-sm text-ink-muted">
          The evaluation campaign has not run yet. Every number, run, and chart on this page is a
          hand-made placeholder fixture demonstrating the final presentation — none of it is
          evidence.
        </p>
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
          Method inspired by{" "}
          <a
            href="https://arxiv.org/abs/2608.11234"
            target="_blank"
            rel="noreferrer"
            className="text-accent hover:underline"
          >
            InfraBench (arXiv:2608.11234)
          </a>
          ; not affiliated with InfraBench.
        </p>
        <p className="mt-3 font-mono text-xs text-ink-faint">
          <a
            href="https://github.com/bingqin2/hy3"
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink"
          >
            Source
          </a>
          {" · "}
          <a
            href="https://github.com/Tencent-Hunyuan/Hy3"
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink"
          >
            Hy3
          </a>
          {" · MIT · palette: Nature (NPG) hue families, dark-surface steps"}
        </p>
      </div>
    </footer>
  );
}
