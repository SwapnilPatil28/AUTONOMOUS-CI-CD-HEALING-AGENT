from typing import List, Literal
from pydantic import BaseModel, HttpUrl, Field

BugType = Literal["LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR", "IMPORT", "INDENTATION"]
FixStatus = Literal["FIXED", "FAILED"]
RunStatus = Literal["QUEUED", "RUNNING", "PASSED", "FAILED"]


class RunRequest(BaseModel):
    repository_url: HttpUrl
    team_name: str = Field(min_length=1)
    team_leader_name: str = Field(min_length=1)
    retry_limit: int = Field(default=5, ge=1, le=20)


class RunResponse(BaseModel):
    run_id: str
    status: RunStatus
    branch_name: str


class FixEntry(BaseModel):
    file: str
    bug_type: BugType
    line_number: int
    commit_message: str
    status: FixStatus
    expected_output: str


class TimelineEntry(BaseModel):
    iteration: int
    retry_limit: int
    status: Literal["PASSED", "FAILED"]
    timestamp: str


class ScoreBreakdown(BaseModel):
    base_score: int
    speed_bonus: int
    efficiency_penalty: int
    final_score: int


class RunDetailsResponse(BaseModel):
    run_id: str
    repository_url: str
    team_name: str
    team_leader_name: str
    branch_name: str
    status: RunStatus
    started_at: str
    completed_at: str | None
    duration_seconds: float | None
    total_failures_detected: int
    total_fixes_applied: int
    commit_count: int
    score: ScoreBreakdown
    fixes: List[FixEntry]
    timeline: List[TimelineEntry]
    error_message: str | None = None
    ci_workflow_url: str | None = None
