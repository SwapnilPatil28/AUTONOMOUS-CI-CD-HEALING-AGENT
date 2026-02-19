export default function FixesAppliedTable({ fixes }) {
  if (!fixes || fixes.length === 0) return null;

  return (
    <section className="card">
      <h2>Fixes Applied Table</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Bug Type</th>
              <th>Line Number</th>
              <th>Commit Message</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {fixes.map((fix, index) => {
              const success = fix.status === "FIXED";
              return (
                <tr key={`${fix.file}-${fix.line_number}-${index}`}>
                  <td>{fix.file}</td>
                  <td>{fix.bug_type}</td>
                  <td>{fix.line_number}</td>
                  <td>{fix.commit_message}</td>
                  <td className={success ? "ok" : "ko"}>{success ? "✓ Fixed" : "✗ Failed"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
