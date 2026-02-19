from __future__ import annotations

import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from app.agents.pipeline import (
    TestDiscoveryAgent,
    TimelineAgent,
)
from app.agents.langgraph_flow import LangGraphOrchestrator
from app.core.policy import build_branch_name
from app.core.scoring import calculate_score
from app.models.api import RunRequest
from app.services.failure_parser import FailureParserService
from app.services.github_ops import GitHubOpsService
from app.services.patch_applier import PatchApplierService
from app.services.static_analyzer import StaticAnalyzerService
from app.services.storage import StorageService
from app.services.test_engine import TestEngineService


class RunnerService:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage
        self.repo_root = Path(__file__).resolve().parents[2]
        self.work_dir = self.repo_root / "workspaces"
        self.work_dir.mkdir(exist_ok=True)

        self.test_discovery_agent = TestDiscoveryAgent()
        self.graph_orchestrator = LangGraphOrchestrator()
        self.timeline_agent = TimelineAgent()
        self.github_ops = GitHubOpsService()
        self.test_engine = TestEngineService()
        self.failure_parser = FailureParserService()
        self.patch_applier = PatchApplierService()
        self.static_analyzer = StaticAnalyzerService()

    def build_initial_state(self, run_id: str, payload: RunRequest, branch_name: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "repository_url": str(payload.repository_url),
            "team_name": payload.team_name,
            "team_leader_name": payload.team_leader_name,
            "branch_name": branch_name,
            "status": "QUEUED",
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
            "duration_seconds": None,
            "total_failures_detected": 0,
            "total_fixes_applied": 0,
            "commit_count": 0,
            "score": {
                "base_score": 100,
                "speed_bonus": 0,
                "efficiency_penalty": 0,
                "final_score": 100,
            },
            "fixes": [],
            "timeline": [],
            "error_message": None,
            "ci_workflow_url": None,
        }

    async def start_run(self, payload: RunRequest) -> str:
        run_id = str(uuid.uuid4())
        branch_name = build_branch_name(payload.team_name, payload.team_leader_name)
        run_state = self.build_initial_state(run_id=run_id, payload=payload, branch_name=branch_name)
        self.storage.upsert_run(run_id, run_state)
        return run_id

    async def execute_run(self, run_id: str, payload: RunRequest) -> None:
        started_at = datetime.now(UTC)
        run_state = self.storage.get_run(run_id)
        run_state["status"] = "RUNNING"
        run_state["started_at"] = started_at.isoformat()
        self.storage.upsert_run(run_id, run_state)

        branch_name = run_state["branch_name"]
        repo_dir = self.work_dir / run_id
        passed = False
        iteration = 0

        try:
            owner, repo = self.github_ops.parse_owner_repo(str(payload.repository_url))
            self.github_ops.clone_repository(str(payload.repository_url), repo_dir)
            self.github_ops.create_branch(repo_dir, branch_name)
            self.test_discovery_agent.discover(repo_dir)

            while iteration < payload.retry_limit and not passed:
                iteration += 1

                local_solved = False
                local_attempts = 0
                max_local_attempts = 3
                iteration_rows: list[dict[str, Any]] = []
                applied_in_iteration = 0

                while local_attempts < max_local_attempts:
                    local_attempts += 1

                    test_result = self.test_engine.run_tests(repo_dir)
                    parsed_failures = self.failure_parser.parse(test_result.output)
                    static_failures = self.static_analyzer.analyze(repo_dir)

                    parsed_failures = self._normalize_failure_paths(parsed_failures, repo_dir)
                    static_failures = self._normalize_failure_paths(static_failures, repo_dir)
                    raw_failures = self._merge_failures(parsed_failures, static_failures)
                    run_state["total_failures_detected"] += len(raw_failures)

                    if not raw_failures:
                        local_solved = True
                        break

                    graph_state = self.graph_orchestrator.run(raw_failures)
                    applied_this_pass = 0

                    for fix_result in graph_state["fix_results"]:
                        fix_plan = fix_result["plan"]
                        source_failure = next(
                            (
                                item
                                for item in raw_failures
                                if item["file"] == fix_plan.file
                                and item["line_number"] == fix_plan.line_number
                                and item["bug_type"] == fix_plan.bug_type
                            ),
                            {"message": ""},
                        )

                        applied = self.patch_applier.apply_fix(
                            repo_path=repo_dir,
                            file_path=fix_plan.file,
                            line_number=fix_plan.line_number,
                            bug_type=fix_plan.bug_type,
                            message=source_failure.get("message", ""),
                        )

                        if applied:
                            applied_this_pass += 1
                            applied_in_iteration += 1
                            run_state["total_fixes_applied"] += 1

                        iteration_rows.append(
                            {
                                "file": fix_plan.file,
                                "bug_type": fix_plan.bug_type,
                                "line_number": fix_plan.line_number,
                                "commit_message": fix_plan.commit_message if applied else "[AI-AGENT] Fix attempt failed",
                                "status": "FIXED" if applied else "FAILED",
                                "expected_output": fix_plan.expected_output,
                            }
                        )

                    if applied_this_pass == 0:
                        break

                if applied_in_iteration > 0:
                    committed, final_commit_message = self.github_ops.commit_changes(
                        repo_path=repo_dir,
                        commit_message=f"Iteration {iteration}: apply {applied_in_iteration} autonomous fixes",
                    )
                    if committed:
                        run_state["commit_count"] += 1
                        for row in iteration_rows:
                            if row["status"] == "FIXED":
                                row["commit_message"] = final_commit_message

                run_state["fixes"].extend(iteration_rows)

                self.github_ops.push_branch(repo_dir, branch_name)
                ci_status, workflow_url = await self.github_ops.poll_ci_status(owner, repo, branch_name)
                run_state["ci_workflow_url"] = workflow_url
                passed = ci_status == "PASSED" and local_solved
                run_state["timeline"].append(
                    self.timeline_agent.event(
                        iteration=iteration,
                        retry_limit=payload.retry_limit,
                        passed=passed,
                    )
                )

                self.storage.upsert_run(run_id, run_state)

            run_state["status"] = "PASSED" if passed else "FAILED"

        except Exception as error:
            run_state["status"] = "FAILED"
            run_state["error_message"] = str(error)
            if iteration > 0:
                run_state["timeline"].append(
                    self.timeline_agent.event(
                        iteration=iteration,
                        retry_limit=payload.retry_limit,
                        passed=False,
                    )
                )

        completed_at = datetime.now(UTC)
        run_state["completed_at"] = completed_at.isoformat()
        run_state["duration_seconds"] = (completed_at - started_at).total_seconds()
        run_state["score"] = calculate_score(
            duration_seconds=run_state["duration_seconds"],
            commit_count=run_state["commit_count"],
        ).model_dump()

        self.storage.upsert_run(run_id, run_state)
        self.storage.write_results_file(run_id, run_state)

    @staticmethod
    def _normalize_failure_paths(failures: list[dict[str, Any]], repo_dir: Path) -> list[dict[str, Any]]:
        repo_root = repo_dir.resolve()
        normalized: list[dict[str, Any]] = []
        for item in failures:
            file_path = item.get("file") or ""
            if file_path and file_path != "unknown":
                path_obj = Path(file_path)
                try:
                    if path_obj.is_absolute():
                        rel_path = path_obj.resolve().relative_to(repo_root)
                        item["file"] = rel_path.as_posix()
                    else:
                        item["file"] = Path(file_path).as_posix()
                except ValueError:
                    item["file"] = Path(file_path).as_posix()
            normalized.append(item)
        return normalized

    @staticmethod
    def _merge_failures(
        failures: list[dict[str, Any]],
        additional_failures: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: dict[tuple[str, int, str], dict[str, Any]] = {}
        for item in [*failures, *additional_failures]:
            key = (item.get("file", "unknown"), item.get("line_number", 1), item.get("bug_type", "LOGIC"))
            merged[key] = item
        return list(merged.values())
