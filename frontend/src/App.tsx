import { Footer, Header, Hero, SampleBanner } from "./components/Chrome";
import { Leaderboard } from "./components/Leaderboard";
import { TaskMatrix } from "./components/TaskMatrix";
import { FailurePatterns } from "./components/FailurePatterns";
import { Taxonomy } from "./components/Taxonomy";
import { RunExplorer } from "./components/RunExplorer";
import { Validation } from "./components/Validation";

export default function App() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <SampleBanner />
        <Leaderboard />
        <TaskMatrix />
        <FailurePatterns />
        <Taxonomy />
        <RunExplorer />
        <Validation />
      </main>
      <Footer />
    </>
  );
}
