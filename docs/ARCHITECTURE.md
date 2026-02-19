# Architecture

```mermaid
flowchart TD
  UI[React Dashboard /frontend] --> API[FastAPI API]
  API --> ORCH[LangGraph Orchestrator]
  ORCH --> DISC[Test Discovery Agent]
  ORCH --> CLASS[Failure Classifier Agent]
  ORCH --> PATCH[Patch Generator Agent]
  ORCH --> VERIFY[Verifier Agent Local Sandbox]
  ORCH --> GITOPS[GitOps Agent]
  GITOPS --> CI[GitHub Actions Polling]
  CI --> ORCH
  ORCH --> STORE[SQLite Storage + results.json]
  STORE --> UI
```

## Key Guarantees
- Branch format is enforced as `TEAM_NAME_LEADER_NAME_AI_Fix`.
- Commit messages are enforced with `[AI-AGENT]` prefix.
- Timeline shows every CI iteration with pass/fail and timestamps.
- `results.json` is generated at end of each run.
