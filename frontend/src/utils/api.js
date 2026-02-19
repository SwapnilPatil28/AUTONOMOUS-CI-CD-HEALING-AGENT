const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function startRun(payload) {
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error("Failed to start run.");
  }

  return response.json();
}

export async function getRun(runId) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch run details.");
  }
  return response.json();
}
