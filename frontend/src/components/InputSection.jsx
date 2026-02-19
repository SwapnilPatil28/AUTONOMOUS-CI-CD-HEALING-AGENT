import { useState } from "react";
import { useRunContext } from "../context/RunContext";

export default function InputSection() {
  const { runAgent, isLoading } = useRunContext();
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [teamName, setTeamName] = useState("");
  const [teamLeaderName, setTeamLeaderName] = useState("");
  const [retryLimit, setRetryLimit] = useState(5);

  const onSubmit = async (event) => {
    event.preventDefault();
    await runAgent({
      repository_url: repositoryUrl,
      team_name: teamName,
      team_leader_name: teamLeaderName,
      retry_limit: Number(retryLimit)
    });
  };

  return (
    <section className="card">
      <h2>Input Section</h2>
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          GitHub Repository URL
          <input
            value={repositoryUrl}
            onChange={(e) => setRepositoryUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            required
            type="url"
          />
        </label>
        <label>
          Team Name
          <input
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            placeholder="RIFT ORGANISERS"
            required
          />
        </label>
        <label>
          Team Leader Name
          <input
            value={teamLeaderName}
            onChange={(e) => setTeamLeaderName(e.target.value)}
            placeholder="Saiyam Kumar"
            required
          />
        </label>
        <label>
          Retry Limit
          <input
            value={retryLimit}
            onChange={(e) => setRetryLimit(e.target.value)}
            type="number"
            min={1}
            max={20}
            required
          />
        </label>
        <button className="primary" disabled={isLoading} type="submit">
          {isLoading ? "Running Agent..." : "Run Agent"}
        </button>
      </form>
      {isLoading && <p className="loading">Loading: Autonomous agent is analyzing the repository.</p>}
    </section>
  );
}
