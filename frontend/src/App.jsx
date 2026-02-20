import InputSection from "./components/InputSection";
import Floww from "./assets/Floww.png";
import RunSummaryCard from "./components/RunSummaryCard";
import ScoreBreakdownPanel from "./components/ScoreBreakdownPanel";
import FixesAppliedTable from "./components/FixesAppliedTable";
import CicdStatusTimeline from "./components/CicdStatusTimeline";
import { useRunContext } from "./context/RunContext";

function App() {
  const { runData, error } = useRunContext();

  return (
    <div className="app-shell">

      <main className="layout">
        <header className="top-header">
          <div>
            <h1>DevOps Healing Dashboard</h1>
            <p>Autonomous CI/CD Pipeline Intelligence</p>
          </div>
        </header>

        <section className="intro-grid">
          <InputSection />
          <div className="intro-right">
            <img src={Floww} alt="Flow diagram" className="intro-image" />
            <p className="intro-text">Autonomous CI/CD Healing Agent analyzes repositories, identifies failures, and proposes fixes to improve pipeline reliability and developer productivity.</p>
          </div>
        </section>

        {error ? (
          <section className="card">
            <p className="ko">{error}</p>
          </section>
        ) : null}

        {runData?.error_message ? (
          <section className="card">
            <p className="ko">{runData.error_message}</p>
          </section>
        ) : null}

        <RunSummaryCard run={runData} />
        <ScoreBreakdownPanel score={runData?.score} />
        <FixesAppliedTable fixes={runData?.fixes} />
        <CicdStatusTimeline timeline={runData?.timeline} />
      </main>
    </div>
  );
}

export default App;