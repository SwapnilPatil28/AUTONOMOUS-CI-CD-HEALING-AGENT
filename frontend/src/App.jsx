import InputSection from "./components/InputSection";
import RunSummaryCard from "./components/RunSummaryCard";
import ScoreBreakdownPanel from "./components/ScoreBreakdownPanel";
import FixesAppliedTable from "./components/FixesAppliedTable";
import CicdStatusTimeline from "./components/CicdStatusTimeline";
import { useRunContext } from "./context/RunContext";

function App() {
  const { runData, error } = useRunContext();

  return (
    <main className="layout">
      <header>
        <h1>Autonomous CI/CD Healing Agent</h1>
        <p>RIFT 2026 Hackathon Dashboard</p>
      </header>

      <InputSection />

      {error ? <section className="card"><p className="ko">{error}</p></section> : null}
      {runData?.error_message ? <section className="card"><p className="ko">{runData.error_message}</p></section> : null}

      <RunSummaryCard run={runData} />
      <ScoreBreakdownPanel score={runData?.score} />
      <FixesAppliedTable fixes={runData?.fixes} />
      <CicdStatusTimeline timeline={runData?.timeline} />
    </main>
  );
}

export default App;
