# Development Notes

## Local startup (split terminals)

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Runtime directories

These are generated during runs and ignored by git:
- `backend/data/`
- `backend/workspaces/`

## Useful test scripts

Repository includes validation scripts:
- `test_all_bug_types.py`
- `test_dashboard_scenario.py`
- `test_rift_compliance.py`
- `backend/test_multi_language.py`
- `backend/test_token.py`

Run example:
```bash
cd backend
python test_multi_language.py
```

## Common failure causes

- Missing or insufficient `GITHUB_TOKEN` permissions
- Target repository branch protection preventing push
- No GitHub Actions workflow in target repository
- Docker unavailable (engine not running), causing fallback execution mode
