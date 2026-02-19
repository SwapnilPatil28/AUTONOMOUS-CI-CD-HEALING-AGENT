import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.runner import RunnerService
from app.services.storage import StorageService
from app.models.api import RunRequest, RunResponse, RunDetailsResponse

app = FastAPI(title="Autonomous CI/CD Healing Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = StorageService()
runner = RunnerService(storage=storage)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/runs", response_model=RunResponse)
async def create_run(payload: RunRequest) -> RunResponse:
    run_id = await runner.start_run(payload)
    run = storage.get_run(run_id)

    if run["status"] == "QUEUED":
        asyncio.create_task(runner.execute_run(run_id=run_id, payload=payload))

    return RunResponse(
        run_id=run_id,
        status=run["status"],
        branch_name=run["branch_name"],
    )


@app.post("/api/runs/{run_id}/resume", response_model=RunResponse)
async def resume_run(run_id: str, payload: RunRequest) -> RunResponse:
    asyncio.create_task(runner.execute_run(run_id=run_id, payload=payload))
    run = storage.get_run(run_id)
    return RunResponse(
        run_id=run_id,
        status=run["status"],
        branch_name=run["branch_name"],
    )


@app.get("/api/runs/{run_id}", response_model=RunDetailsResponse)
async def get_run(run_id: str) -> RunDetailsResponse:
    run = storage.get_run(run_id)
    return RunDetailsResponse(**run)
