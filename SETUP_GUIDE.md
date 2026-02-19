# Complete Setup Guide for Autonomous CI/CD Healing Agent

## Prerequisites Checklist
- [ ] GitHub account with at least one repository you own
- [ ] Python 3.10+ installed (you have Anaconda)
- [ ] Node.js 18+ installed (for frontend)
- [ ] Git installed on your machine
- [ ] Text editor (VS Code recommended)

---

## Part 1: Prepare Your Test Repository

### Step 1.1: Choose or Create a Repository
**What:** Pick a GitHub repository where you have admin/write access.

**Where:** https://github.com/YOUR-USERNAME

**Actions:**
1. Open GitHub.com in your browser
2. Sign in to your account
3. Go to your profile → Repositories tab
4. Either:
   - **Option A:** Select an existing repo you own
   - **Option B:** Click "New" → Create a test repo (e.g., `cicd-test-project`)
     - Make it **Public** or **Private** (both work)
     - Initialize with README
     - Add a simple Python test file later

**Why:** The agent needs write access to create branches and push commits. You must be the owner or have collaborator write access.

**Result:** You have a repo URL like `https://github.com/YOUR-USERNAME/cicd-test-project`

---

### Step 1.2: Enable GitHub Actions in Your Repo
**What:** Ensure GitHub Actions can run automated tests.

**Where:** Your repo → Settings → Actions → General

**Actions:**
1. In your chosen repository, click **"Settings"** tab (top menu)
2. Scroll down left sidebar → Click **"Actions"** → **"General"**
3. Under "Actions permissions", ensure:
   - ✅ "Allow all actions and reusable workflows" is selected
   - OR ✅ "Allow [owner] actions and reusable workflows"
4. Scroll down → Under "Workflow permissions":
   - ✅ Select "Read and write permissions"
   - ✅ Check "Allow GitHub Actions to create and approve pull requests"
5. Click **"Save"**

**Why:** The agent polls GitHub Actions workflow runs to determine CI pass/fail status.

**Result:** Actions are enabled and have write permissions.

---

### Step 1.3: Add a Simple Workflow File (if none exists)
**What:** Create a basic CI workflow that runs tests.

**Where:** Your repo → `.github/workflows/ci.yml`

**Actions:**
1. In your repository, click **"Add file"** → **"Create new file"**
2. File path: `.github/workflows/ci.yml`
3. Paste this content:

```yaml
name: CI Tests

on:
  push:
    branches: ['**']
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
      
      - name: Run tests
        run: |
          pytest --verbose || echo "No tests found"
```

4. Commit directly to `main` branch
5. Go to **"Actions"** tab → Confirm the workflow appears

**Why:** The agent needs a workflow to trigger when it pushes the AI fix branch. This workflow runs tests and reports pass/fail.

**Result:** You have a working CI pipeline.

---

### Step 1.4: Add a Sample Buggy Test File (Optional but Recommended)
**What:** Create a Python file with intentional bugs for the agent to fix.

**Where:** Your repo → `test_sample.py`

**Actions:**
1. In your repository, click **"Add file"** → **"Create new file"**
2. File path: `test_sample.py`
3. Paste this buggy code:

```python
# Intentional bugs for AI agent to detect and fix

import os  # Unused import (LINTING bug)

def add_numbers(a, b)  # Missing colon (SYNTAX bug)
    return a + b

def test_addition():
    assert add_numbers(2, 3) == 5
```

4. Commit to `main` branch

**Why:** This gives the agent actual failures to detect, classify, and fix. Without bugs, the agent completes immediately with 0 fixes.

**Result:** Your repo now has code that will fail CI, ready for autonomous healing.

---

## Part 2: Create GitHub Personal Access Token

### Step 2.1: Navigate to Token Settings
**What:** Generate a token that lets the agent authenticate as you.

**Where:** GitHub → Settings → Developer settings → Tokens

**Actions:**
1. Click your **profile picture** (top-right of GitHub)
2. Click **"Settings"**
3. Scroll down the left sidebar to bottom
4. Click **"Developer settings"** (second to last option)
5. Click **"Personal access tokens"** → **"Fine-grained tokens"**
6. Click **"Generate new token"**

**Why:** Fine-grained tokens are more secure (repo-specific) than classic tokens.

---

### Step 2.2: Configure Token Details
**What:** Name and scope your token.

**Where:** Token creation form

**Actions - Fill each field:**

1. **Token name:** `CICD-Agent-Token`
2. **Expiration:** `90 days` (or `Custom` → select deadline after Feb 28, 2026)
3. **Description:** `Token for autonomous CI/CD healing agent`
4. **Resource owner:** Select your username
5. **Repository access:** 
   - ✅ Select **"Only select repositories"**
   - From dropdown, choose your test repo (e.g., `cicd-test-project`)

**Why:** Limiting to specific repos follows security best practices.

---

### Step 2.3: Set Repository Permissions
**What:** Grant exact permissions the agent needs.

**Where:** Still in token creation form → "Repository permissions" section

**Actions - Expand and configure these:**

| Permission | Access Level | Why |
|------------|-------------|-----|
| **Contents** | ✅ **Read and write** | Push branches and commits |
| **Metadata** | ✅ **Read-only** (auto-selected) | Access repo info |
| **Actions** | ✅ **Read-only** | Poll workflow run status |
| **Workflows** | ✅ **Read and write** (optional) | Trigger workflows if needed |

**Scroll through all permissions** and leave others at "No access" unless you know you need them.

---

### Step 2.4: Generate and Copy Token
**What:** Create the token and save it securely.

**Actions:**
1. Scroll to bottom of form
2. Click **"Generate token"** (green button)
3. You'll see a page with:
   - ✅ Token value starting with `github_pat_...`
4. Click **"Copy"** icon next to the token
5. **IMMEDIATELY paste it somewhere safe** (Notepad, password manager)
   - You'll use this in `.env` file next
   - ⚠️ GitHub shows this token **ONLY ONCE**
   - If you lose it, delete and regenerate

**Why:** This token is your agent's authentication credential. Treat it like a password.

**Result:** You have a token string like `github_pat_11ABC...XYZ123`

---

## Part 3: Configure Backend Environment

### Step 3.1: Open Project in Terminal
**What:** Navigate to backend directory.

**Actions:**
1. Open **PowerShell** (Windows search → "PowerShell")
2. Run:
```powershell
Set-Location "c:/Users/sampa/OneDrive/Desktop/Git Repos/AUTONOMOUS-CI-CD-HEALING-AGENT/backend"
```

**Why:** All backend setup commands run from this directory.

---

### Step 3.2: Create Environment File
**What:** Copy the example env file and add your secrets.

**Actions:**
1. In PowerShell, run:
```powershell
Copy-Item .env.example .env
```

2. Open `.env` file in text editor:
```powershell
notepad .env
```

3. You'll see template content. Replace with your values:

```env
# GitHub Authentication
GITHUB_TOKEN=github_pat_YOUR_ACTUAL_TOKEN_HERE

# Optional: Default metadata (agent also parses from URL)
GITHUB_OWNER=YOUR-GITHUB-USERNAME
GITHUB_REPO=cicd-test-project

# Optional: Runtime config
DEFAULT_RETRY_LIMIT=5
LOG_LEVEL=INFO
```

**Example filled `.env`:**
```env
GITHUB_TOKEN=github_pat_11ABCDEFGHIJ1234567890KLMNOPqrstuvwxyz
GITHUB_OWNER=sampa-dev
GITHUB_REPO=test-project
DEFAULT_RETRY_LIMIT=5
LOG_LEVEL=INFO
```

4. **Save and close** the file (Ctrl+S, then X in Notepad)

**Why:** 
- `GITHUB_TOKEN`: Lets agent clone/push to your repo
- `GITHUB_OWNER` / `GITHUB_REPO`: Optional fallbacks (agent parses from input URL)
- `DEFAULT_RETRY_LIMIT`: Max healing iterations if not specified in dashboard

**Security:** `.env` is in `.gitignore` so it won't accidentally commit to GitHub.

---

### Step 3.3: Install Backend Dependencies
**What:** Install all Python packages the agent needs.

**Actions:**
1. In PowerShell (still in `backend/` directory), run:
```powershell
C:/Users/sampa/anaconda3/python.exe -m pip install -r requirements.txt
```

2. Wait for installation (~1-2 minutes)
3. Look for success messages, no red error text

**What gets installed:**
- `fastapi` - Web API framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `httpx` - HTTP client for GitHub API
- `GitPython` - Git operations (clone/commit/push)
- `langgraph` - Multi-agent orchestration
- `langchain` - Agent framework
- Other utilities

**Why:** These libraries enable autonomous repo operations, API serving, and agent decision-making.

**Troubleshooting:**
- If `pip install` fails with "no module named pip": 
  ```powershell
  C:/Users/sampa/anaconda3/python.exe -m ensurepip --upgrade
  ```

---

### Step 3.4: Start Backend Server
**What:** Run the FastAPI backend that orchestrates the agent.

**Actions:**
1. In PowerShell (still in `backend/`), run:
```powershell
C:/Users/sampa/anaconda3/python.exe -m uvicorn app.main:app --port 8000
```

2. You'll see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [67890]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

3. **Leave this terminal running** - don't close it!

**What this means:**
- `uvicorn` = Production-grade Python web server
- `app.main:app` = Load the FastAPI application from `app/main.py`
- `--port 8000` = Listen on http://127.0.0.1:8000

**Important:** Do not use `--reload` while running autonomous healing. The agent edits files inside `backend/workspaces/`, and auto-reload can restart the backend mid-run.

**Why:** This API endpoint receives dashboard requests and triggers autonomous healing runs.

**How to verify it's working:**
1. Open browser
2. Go to: http://127.0.0.1:8000/docs
3. You should see FastAPI interactive documentation (Swagger UI)
4. Endpoints listed: `/health`, `/api/runs`, `/api/runs/{run_id}`

---

## Part 4: Configure and Start Frontend

### Step 4.1: Open New Terminal for Frontend
**What:** Start frontend in separate terminal (backend must stay running).

**Actions:**
1. Open **new PowerShell window** (don't close backend terminal!)
2. Navigate to frontend:
```powershell
Set-Location "c:/Users/sampa/OneDrive/Desktop/Git Repos/AUTONOMOUS-CI-CD-HEALING-AGENT/frontend"
```

---

### Step 4.2: Install Frontend Dependencies
**What:** Install React and visualization libraries.

**Actions:**
1. In frontend terminal, run:
```powershell
npm install
```

2. Wait for installation (~30-60 seconds)
3. Look for output ending with:
```
added 245 packages, and audited 246 packages in 45s
```

**What gets installed:**
- `react` / `react-dom` - UI framework
- `recharts` - Score breakdown charts
- `vite` - Lightning-fast build tool
- Other dependencies

**Why:** Dashboard needs these to render the 5 required sections interactively.

**Troubleshooting:**
- If `npm: command not found`: Install Node.js from https://nodejs.org (LTS version)
- If `EACCES` permissions error: Run PowerShell as Administrator

---

### Step 4.3: Start Development Server
**What:** Launch the React dashboard.

**Actions:**
1. In frontend terminal, run:
```powershell
npm run dev
```

2. You'll see:
```
  VITE v6.4.1  ready in 324 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

3. **Leave this terminal running** too!

**What this means:**
- Dashboard is live at `http://localhost:5173`
- Hot reload enabled (edits auto-refresh browser)

**How to verify:**
1. Open browser
2. Go to: http://localhost:5173
3. You should see:
   - Header: "Autonomous CI/CD Healing Agent"
   - Input Section with form fields
   - Empty panels below (will populate after run)

---

## Part 5: Run the Autonomous Agent

### Step 5.1: Fill Dashboard Input Form
**What:** Configure a healing run for your test repo.

**Where:** http://localhost:5173 → Input Section

**Actions - Fill each field:**

1. **GitHub Repository URL**
   - Paste: `https://github.com/YOUR-USERNAME/cicd-test-project`
   - Example: `https://github.com/sampa-dev/test-project`
   - Why: Agent clones this repo

2. **Team Name**
   - Type: `RIFT ORGANISERS`
   - Must be uppercase with spaces (agent auto-converts)
   - Why: Used in branch name

3. **Team Leader Name** 
   - Type: `Saiyam Kumar`
   - Your actual name or test name
   - Why: Used in branch name

4. **Retry Limit**
   - Type: `5`
   - Range: 1-20
   - Why: Max healing iterations before giving up

**Expected branch name preview:** `RIFT_ORGANISERS_SAIYAM_KUMAR_AI_Fix`

---

### Step 5.2: Trigger the Agent
**What:** Start autonomous healing process.

**Actions:**
1. Click **"Run Agent"** button (blue, bottom of form)
2. Button changes to: "Running Agent..." (disabled, orange)
3. Loading message appears: "Loading: Autonomous agent is analyzing the repository."

**What happens behind the scenes:**
1. Dashboard sends POST request to backend: `http://127.0.0.1:8000/api/runs`
2. Backend creates run ID, queues it
3. Background task starts:
   - Clone repo to `backend/workspaces/{run_id}/`
   - Create branch with exact naming format
   - Checkout branch
   - Run test command detection
   - Execute tests (pytest/npm test/etc)
   - Parse failures from output
   - Classify bugs (LINTING/SYNTAX/LOGIC/etc)
   - Generate fix plans via LangGraph agents
   - Apply patches to source files
   - Commit with `[AI-AGENT]` prefix
   - Push branch to GitHub
   - Poll GitHub Actions API for workflow status
   - If failed: detect remaining issues, iterate
   - If passed: calculate score, finalize results
4. Dashboard polls every 2.5 seconds for status update

---

### Step 5.3: Watch Real-Time Progress
**What:** Monitor agent progress in dashboard.

**Where:** Dashboard updates automatically as agent works.

**What you'll see (in order):**

1. **Run Summary Card** (appears first)
   - Repository URL
   - Team Name / Leader Name
   - Branch Name (verify exact format!)
   - Status badge (orange "RUNNING")
   - Counters start at 0

2. **Score Breakdown Panel** (updates)
   - Base Score: 100
   - Speed Bonus: increases if fast
   - Efficiency Penalty: increases with retries
   - Final Score: calculated
   - Bar chart visualizes breakdown

3. **Fixes Applied Table** (rows appear)
   - Each fix shows:
     - File path (e.g., `test_sample.py`)
     - Bug type (e.g., `SYNTAX`)
     - Line number (e.g., `5`)
     - Commit message (starts with `[AI-AGENT]`)
     - Status: ✓ Fixed (green) or ✗ Failed (red)
   - Expected Output column shows what was fixed

4. **CI/CD Status Timeline** (events log)
   - Each iteration creates entry:
     - Iteration: `1/5`, `2/5`, etc.
     - Status: FAILED (red) or PASSED (green)
     - Timestamp: ISO format

**Expected flow:**
- Iteration 1: FAILED (bugs detected, fixes committed)
- Iteration 2: PASSED (all tests green)
- Status changes from RUNNING → PASSED

**Duration:** 2-5 minutes depending on repo size and CI queue.

---

### Step 5.4: Verify on GitHub
**What:** Confirm agent created branch and commits correctly.

**Where:** Your GitHub repository webpage.

**Actions:**
1. Open GitHub.com in browser
2. Go to your test repository
3. Click **branch dropdown** (shows "main" by default)
4. Look for new branch: `RIFT_ORGANISERS_SAIYAM_KUMAR_AI_Fix`

**Click the branch, then verify:**

1. **Branch exists** with exact name format
   - Must be: `TEAM_NAME_LEADER_NAME_AI_Fix`
   - Uppercase, underscores, exact suffix

2. **Commits visible** in history
   - Click "Commits" or view file changes
   - Each commit message starts with: `[AI-AGENT]`
   - Example: `[AI-AGENT] Fix SYNTAX in test_sample.py:5`

3. **Actions workflow ran**
   - Click "Actions" tab
   - Find workflow run for your AI branch
   - Click it → See test results
   - Final status: ✓ (green checkmark)

4. **Source files changed**
   - View `test_sample.py` on the AI branch
   - Compare to `main` branch
   - Bugs should be fixed:
     - Unused import removed
     - Missing colon added
     - Tests now pass

**Why this matters:** These are the exact judging criteria from problem statement.

---

### Step 5.5: Check Results File
**What:** Verify JSON output was generated.

**Where:** `backend/data/results.json`

**Actions:**
1. In file explorer or VS Code, navigate to:
   ```
   c:\Users\sampa\OneDrive\Desktop\Git Repos\AUTONOMOUS-CI-CD-HEALING-AGENT\backend\data\
   ```

2. Open `results.json` in text editor

3. Verify structure matches sample:
```json
{
  "run_id": "uuid-here",
  "repository_url": "https://github.com/...",
  "team_name": "RIFT ORGANISERS",
  "team_leader_name": "Saiyam Kumar",
  "branch_name": "RIFT_ORGANISERS_SAIYAM_KUMAR_AI_Fix",
  "status": "PASSED",
  "started_at": "2026-02-19T...",
  "completed_at": "2026-02-19T...",
  "duration_seconds": 123.45,
  "total_failures_detected": 2,
  "total_fixes_applied": 2,
  "commit_count": 2,
  "score": {
    "base_score": 100,
    "speed_bonus": 10,
    "efficiency_penalty": 0,
    "final_score": 110
  },
  "fixes": [ ... ],
  "timeline": [ ... ]
}
```

**Why:** This is submission artifact judges will review.

---

## Part 6: Troubleshooting Common Issues

### Issue 1: "403 Forbidden" on Push
**Error in dashboard:** `git push failed due to: exit code(128) ... error: 403`

**Cause:** Token lacks write permission or wrong repo selected.

**Fix:**
1. Go to GitHub → Settings → Developer settings → Tokens
2. Click your token → Edit
3. Verify:
   - Repository access includes your test repo
   - Contents permission = "Read and write"
4. If wrong, regenerate token with correct settings
5. Update `backend/.env` with new token
6. Restart backend server (Ctrl+C, then re-run uvicorn command)

---

### Issue 2: Timeline Shows 0 Iterations
**Symptom:** Run completes immediately, no timeline entries.

**Cause:** Agent couldn't run tests or parse failures.

**Fix:**
1. Check backend terminal for error messages
2. Verify test file exists in repo
3. Ensure workflow file exists in `.github/workflows/`
4. Try manual test run:
   ```powershell
   cd backend/workspaces/{run-id}/
   python -m pytest
   ```
5. If tests don't exist, add sample test file (see Part 1.4)

---

### Issue 3: CI Status Stays "RUNNING" Forever
**Symptom:** Dashboard shows orange "RUNNING" for 10+ minutes.

**Cause:** GitHub Actions workflow not configured or disabled.

**Fix:**
1. Open GitHub repo → Actions tab
2. Check if workflows are disabled
3. Enable workflows if needed
4. Verify `.github/workflows/ci.yml` exists
5. Manually trigger workflow to test
6. Check Actions run logs for errors

---

### Issue 4: Branch Name Format Wrong
**Symptom:** Branch created as `rift-organisers-saiyam-kumar-ai-fix` (lowercase/hyphens).

**Cause:** Policy enforcement bug (shouldn't happen with current code).

**Fix:**
1. Check `backend/app/core/policy.py` → `build_branch_name()` function
2. Ensure `sanitize_name()` uses `.upper()` and `'_'.join()`
3. If modified, revert to original implementation
4. Restart backend

---

### Issue 5: Frontend Shows "Failed to fetch"
**Symptom:** Red error message when clicking Run Agent.

**Cause:** Backend not running or wrong port.

**Fix:**
1. Check backend terminal - should show "Uvicorn running..."
2. Test backend directly: Open http://127.0.0.1:8000/health
3. Should return: `{"status": "ok"}`
4. If not, restart backend
5. Check frontend `src/utils/api.js` → `API_BASE` should be `http://127.0.0.1:8000`

---

### Issue 6: No Fixes Detected
**Symptom:** Run shows PASSED but 0 fixes applied.

**Cause:** No bugs existed in repo, or test file has no issues.

**Fix:**
1. Add intentional bugs to test file (see Part 1.4)
2. Run agent again
3. Or test with repo that has known flaky tests

---

## Part 7: Submission Preparation

### Step 7.1: Record Demo Video
**What:** Screen recording showing complete autonomous flow.

**Required content:**
1. Show dashboard input form filled
2. Click "Run Agent"
3. Show all 5 panels populating in real-time
4. Switch to GitHub → show branch + commits + Actions
5. Return to dashboard → show final PASSED status
6. Show `results.json` file content

**Tools:** OBS Studio, Windows Game Bar (Win+G), or Loom

**Duration:** 3-5 minutes

---

### Step 7.2: Deploy to Production (Optional)
**What:** Host on cloud for judges to test live.

**Options:**

**Backend (Railway):**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
cd backend
railway init
railway up
```

**Frontend (Vercel):**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel
```

Update frontend `VITE_API_BASE` to point to Railway backend URL.

---

### Step 7.3: Update README with Links
**What:** Add your deployment URLs and video link.

**Actions:**
1. Open `README.md`
2. Fill these sections:
   - Deployment URL: `https://your-app.vercel.app`
   - Video Demo: `https://youtube.com/watch?v=...`
   - GitHub Repo: `https://github.com/YOUR-USERNAME/AUTONOMOUS-CI-CD-HEALING-AGENT`
   - Team Leader LinkedIn: Your profile URL

---

## Quick Reference Commands

### Start Backend
```powershell
cd "c:/Users/sampa/OneDrive/Desktop/Git Repos/AUTONOMOUS-CI-CD-HEALING-AGENT/backend"
C:/Users/sampa/anaconda3/python.exe -m uvicorn app.main:app --port 8000
```

### Start Frontend
```powershell
cd "c:/Users/sampa/OneDrive/Desktop/Git Repos/AUTONOMOUS-CI-CD-HEALING-AGENT/frontend"
npm run dev
```

### Check Backend Health
Open: http://127.0.0.1:8000/health

### Check Dashboard
Open: http://localhost:5173

### View Results
File: `backend/data/results.json`

---

## Success Checklist

Before final submission, verify:

- [ ] Token has Contents: Read+Write permission
- [ ] Test repo has GitHub Actions enabled
- [ ] Workflow file exists at `.github/workflows/ci.yml`
- [ ] Backend `.env` file contains valid `GITHUB_TOKEN`
- [ ] Backend starts without errors (uvicorn running)
- [ ] Frontend starts and loads at localhost:5173
- [ ] Dashboard shows all 5 required sections
- [ ] Test run creates branch with EXACT format: `TEAM_NAME_LEADER_NAME_AI_Fix`
- [ ] All commits start with `[AI-AGENT]`
- [ ] Timeline shows iterations with timestamps
- [ ] Final status is PASSED or FAILED (not stuck RUNNING)
- [ ] `results.json` file generated in `backend/data/`
- [ ] GitHub repo shows AI branch + commits + Actions run
- [ ] Demo video recorded showing complete flow
- [ ] README updated with deployment URL + video link

---

## Need Help?

**Backend logs:** Check PowerShell terminal running uvicorn - shows detailed agent execution.

**Frontend console:** Open browser DevTools (F12) → Console tab - shows API errors.

**GitHub API limits:** Free tier = 60 requests/hour without token, 5000/hour with token.

**Test without pushing:** Set `GITHUB_TOKEN=` (empty) in `.env` to test failure handling.

---

You're now ready to run fully autonomous CI/CD healing! Follow Part 5 to execute your first run.
