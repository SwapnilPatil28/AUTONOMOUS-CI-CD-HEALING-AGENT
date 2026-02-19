# Autonomous CI/CD Healing Agent

RIFT 2026 Hackathon submission for the AI/ML + DevOps Automation + Agentic Systems track.

## Live Deployment URL
- Frontend: `ADD_YOUR_DEPLOYED_FRONTEND_URL`

## LinkedIn Demo Video URL
- `ADD_YOUR_LINKEDIN_VIDEO_URL` (must tag @RIFT2026 and remain public)

## Project Architecture Diagram
- See `docs/ARCHITECTURE.md`

## Team Members
- Team Name: `ADD_TEAM_NAME`
- Team Leader: `ADD_TEAM_LEADER_NAME`
- Members: `ADD_MEMBER_NAMES`

## Core Features
- Accepts GitHub repository URL, team name, and leader name from React dashboard.
- Creates strict branch name format: `TEAM_NAME_LEADER_NAME_AI_Fix`.
- Detects failures, classifies bug types, generates targeted fixes, and commits with `[AI-AGENT]` prefix.
- Monitors CI/CD timeline with iteration status and timestamps.
- Generates `results.json` at the end of each run.

## Mandatory Bug Types Supported
- `LINTING`
- `SYNTAX`
- `LOGIC`
- `TYPE_ERROR`
- `IMPORT`
- `INDENTATION`

## Required Dashboard Sections Implemented
1. Input Section
2. Run Summary Card
3. Score Breakdown Panel
4. Fixes Applied Table
5. CI/CD Status Timeline

## Exact Test Case Output Format
The dashboard stores and displays exact per-fix output strings in this format:

- `LINTING error in src/utils.py line 15 → Fix: remove the import statement`
- `SYNTAX error in src/validator.py line 8 → Fix: add the colon at the correct position`

## Tech Stack
- Frontend: React (functional components + hooks), Context API, Recharts, Vite
- Backend: FastAPI, LangGraph multi-agent orchestration, SQLite
- Sandbox/Execution: Docker (`backend/Dockerfile`, `docker-compose.yml`)

## Repository Structure
- `frontend/` React dashboard (judge-facing interface)
- `backend/` FastAPI + LangGraph agent engine
- `docs/` architecture and design assets
- `samples/` sample `results.json`

## Setup Instructions
### 1) Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --port 8000
```

Set required backend env in `.env`:
- `GITHUB_TOKEN` (Personal Access Token with repo + workflow access)
- `GITHUB_OWNER` and `GITHUB_REPO` (optional metadata)
- `DEFAULT_RETRY_LIMIT` (optional)

### 2) Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and backend runs at `http://localhost:8000`.

Do not run backend with `--reload` during autonomous runs, because file edits in `backend/workspaces` can trigger process restarts.

## Docker Run (Recommended)
```bash
docker compose up --build
```

## API Usage Example
### Start run
`POST /api/runs`

Request body:
```json
{
	"repository_url": "https://github.com/example/project",
	"team_name": "RIFT ORGANISERS",
	"team_leader_name": "Saiyam Kumar",
	"retry_limit": 5
}
```

### Get run details
`GET /api/runs/{run_id}`

## Scoring Logic
- Base score: `100`
- Speed bonus: `+10` if runtime < 5 minutes
- Efficiency penalty: `-2` per commit over 20
- Final score shown in dashboard and `results.json`

## Branch and Commit Compliance Rules
- Branch format must be exactly `TEAM_NAME_LEADER_NAME_AI_Fix`
- Branch values are uppercased, spaces become underscores, special characters are removed
- Commit messages must start with `[AI-AGENT]`
- Agent must never push directly to `main`

## Operational Notes
- GitHub Actions workflow must exist in the target repository for CI polling to produce pass/fail conclusions.
- For public repos where your token has no push permission, the run ends in `FAILED` with error details shown in dashboard.
- Agent behavior remains autonomous once a run starts; no manual patching/hardcoded test paths are used.

## Submission Checklist
- [ ] Public GitHub repository URL
- [ ] Live deployed dashboard URL
- [ ] LinkedIn video URL (2–3 min, tags @RIFT2026)
- [ ] README completed with final team/deployment/video values
- [ ] Architecture walkthrough included in demo

