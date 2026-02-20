# API Reference

Base URL (local default): `http://127.0.0.1:8000`

## Endpoints

### `GET /health`
Returns service liveness.

**Response**
```json
{
  "status": "ok"
}
```

---

### `POST /api/runs`
Create and start a new autonomous run.

**Request body**
```json
{
  "repository_url": "https://github.com/owner/repo",
  "team_name": "My Team",
  "team_leader_name": "Team Lead",
  "retry_limit": 5
}
```

**Validation**
- `repository_url`: valid URL
- `team_name`: non-empty
- `team_leader_name`: non-empty
- `retry_limit`: integer `1..20` (default `5`)

**Response**
```json
{
  "run_id": "uuid",
  "status": "QUEUED",
  "branch_name": "TEAM_NAME_TEAM_LEAD_AI_Fix"
}
```

---

### `GET /api/runs/{run_id}`
Get full run details.

**Response shape**
```json
{
  "run_id": "uuid",
  "repository_url": "https://github.com/owner/repo",
  "team_name": "My Team",
  "team_leader_name": "Team Lead",
  "branch_name": "TEAM_NAME_TEAM_LEAD_AI_Fix",
  "status": "RUNNING",
  "started_at": "2026-02-20T12:34:56.000000+00:00",
  "completed_at": null,
  "duration_seconds": null,
  "total_failures_detected": 0,
  "total_fixes_applied": 0,
  "commit_count": 0,
  "score": {
    "base_score": 100,
    "speed_bonus": 0,
    "efficiency_penalty": 0,
    "final_score": 100
  },
  "fixes": [],
  "timeline": [],
  "error_message": null,
  "ci_workflow_url": null
}
```

**Statuses**
- `QUEUED`
- `RUNNING`
- `PASSED`
- `FAILED`

---

### `POST /api/runs/{run_id}/resume`
Resume an existing run using a request body compatible with `POST /api/runs`.

**Request body**
Same as create-run payload.

**Response**
```json
{
  "run_id": "uuid",
  "status": "RUNNING",
  "branch_name": "TEAM_NAME_TEAM_LEAD_AI_Fix"
}
```

## Fix entry schema

Each item in `fixes` is:

```json
{
  "file": "src/example.py",
  "bug_type": "SYNTAX",
  "line_number": 10,
  "commit_message": "[AI-AGENT] ...",
  "status": "FIXED",
  "expected_output": "SYNTAX error in src/example.py line 10 → Fix: add the colon at the correct position"
}
```

`bug_type` values:
- `LINTING`
- `SYNTAX`
- `LOGIC`
- `TYPE_ERROR`
- `IMPORT`
- `INDENTATION`

`status` values:
- `FIXED`
- `FAILED`
