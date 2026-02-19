export default function CicdStatusTimeline({ timeline }) {
  if (!timeline || timeline.length === 0) return null;

  return (
    <section className="card">
      <h2>CI/CD Status Timeline</h2>
      <ul className="timeline">
        {timeline.map((entry, index) => (
          <li key={`${entry.timestamp}-${index}`}>
            <div>
              <strong>Iteration:</strong> {entry.iteration}/{entry.retry_limit}
            </div>
            <div>
              <strong>Status:</strong> <span className={entry.status === "PASSED" ? "status passed" : "status failed"}>{entry.status}</span>
            </div>
            <div>
              <strong>Timestamp:</strong> {new Date(entry.timestamp).toLocaleString()}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
