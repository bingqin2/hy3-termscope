import { useEffect, useState } from "react";
import { Footer, Header, Hero } from "./components/Chrome";
import { Leaderboard } from "./components/Leaderboard";
import { TaskMatrix } from "./components/TaskMatrix";
import { FailurePatterns } from "./components/FailurePatterns";
import { Taxonomy } from "./components/Taxonomy";
import { RunExplorer } from "./components/RunExplorer";
import { Validation } from "./components/Validation";

export const PAGE_IDS = [
  "leaderboard",
  "per-task",
  "failure-patterns",
  "taxonomy",
  "run-explorer",
  "validation",
] as const;
export type PageId = (typeof PAGE_IDS)[number];

function currentPage(): PageId {
  const h = window.location.hash.replace(/^#\/?/, "");
  return (PAGE_IDS as readonly string[]).includes(h) ? (h as PageId) : "leaderboard";
}

/** Hash-routed pages: each section stands alone instead of one long scroll. */
export default function App() {
  const [page, setPage] = useState<PageId>(currentPage);
  useEffect(() => {
    const onHash = () => {
      setPage(currentPage());
      window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <>
      <Header active={page} />
      <main>
        {page === "leaderboard" && (
          <>
            <Hero />
            <Leaderboard />
          </>
        )}
        {page === "per-task" && <TaskMatrix />}
        {page === "failure-patterns" && <FailurePatterns />}
        {page === "taxonomy" && <Taxonomy />}
        {page === "run-explorer" && <RunExplorer />}
        {page === "validation" && <Validation />}
      </main>
      <Footer />
    </>
  );
}
