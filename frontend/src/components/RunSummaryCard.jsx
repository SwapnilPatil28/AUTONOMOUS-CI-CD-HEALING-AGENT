export default function RunSummaryCard({ run }) {
  if (!run) return null;
  const statusClass =
    run.status === "PASSED"
      ? "status passed"
      : run.status === "FAILED"
        ? "status failed"
        : "status running";

  return (
    <section className="card">
      <h2>Run Summary Card</h2>
      <div className="summary-grid">
        <p><strong>Repository URL:</strong> {run.repository_url}</p>
        <p><strong>Team Name:</strong> {run.team_name}</p>
        <p><strong>Team Leader Name:</strong> {run.team_leader_name}</p>
        <p><strong>Branch Name:</strong> {run.branch_name}</p>
        <p><strong>Total Failures Detected:</strong> {run.total_failures_detected}</p>
        <p><strong>Total Fixes Applied:</strong> {run.total_fixes_applied}</p>
        <p><strong>Total Time Taken:</strong> {run.duration_seconds ? `${run.duration_seconds.toFixed(2)}s` : "-"}</p>
        <p><strong>Final CI/CD Status:</strong> <span className={statusClass}>{run.status}</span></p>
      </div>
    </section>
  );
}
