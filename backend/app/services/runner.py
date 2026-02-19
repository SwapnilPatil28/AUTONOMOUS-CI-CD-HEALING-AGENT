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
        self.test_engine = TestEngineService(use_docker=True)  # ✅ SANDBOXED DOCKER EXECUTION
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
        
        # Track unique failures and successful fixes across iterations
        unique_failures: set[tuple] = set()
        successfully_fixed: set[tuple] = set()  # Fixed failures to avoid retrying
        failed_attempts: dict[tuple, int] = {}  # Track retry attempts per failure
        max_attempts_per_failure = 3
        unique_failures: set[tuple[str, int, str]] = set()
        # Track failed attempts per unique failure to prevent infinite retry
        failed_attempts: dict[tuple[str, int, str], int] = {}
        max_attempts_per_failure = 3

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
                    
                    # Track unique failures across iterations (avoid duplicates)
                    for failure in raw_failures:
                        failure_key = (failure["file"], failure["line_number"], failure["bug_type"])
                        if failure_key not in unique_failures:
                            unique_failures.add(failure_key)
                            run_state["total_failures_detected"] += 1
                    
                    # Remove failures that have already been fixed in previous iterations
                    raw_failures_to_fix = []
                    for f in raw_failures:
                        failure_key = (f["file"], f["line_number"], f["bug_type"])
                        # Skip if already successfully fixed before
                        if failure_key not in successfully_fixed:
                            raw_failures_to_fix.append(f)
                    
                    # If no failures left to fix, we're done
                    if not raw_failures_to_fix:
                        local_solved = True
                        break

                    graph_state = self.graph_orchestrator.run(raw_failures_to_fix)
                    
                    # Deduplicate fix results by (file, line, bug_type)
                    # This handles cases where multiple failures on same line (e.g., multi-part imports)
                    # produce duplicate fix attempts
                    seen_fixes: dict[tuple[str, int, str], dict] = {}
                    for fix_result in graph_state["fix_results"]:
                        fix_plan = fix_result["plan"]
                        fix_key = (fix_plan.file, fix_plan.line_number, fix_plan.bug_type)
                        if fix_key not in seen_fixes:
                            seen_fixes[fix_key] = fix_result
                    
                    deduplicated_fixes = list(seen_fixes.values())
                    
                    # Group fix results by file and sort descending by line number
                    # This prevents line number invalidation when removing lines
                    fixes_by_file: dict[str, list] = {}
                    for fix_result in deduplicated_fixes:
                        fix_plan = fix_result["plan"]
                        if fix_plan.file not in fixes_by_file:
                            fixes_by_file[fix_plan.file] = []
                        fixes_by_file[fix_plan.file].append(fix_result)
                    
                    # Sort each file's fixes by line number (descending)
                    for file_fixes in fixes_by_file.values():
                        file_fixes.sort(key=lambda x: x["plan"].line_number, reverse=True)
                    
                    # Flatten back to a single list (grouped by file, sorted within each file)
                    sorted_fix_results = []
                    for file_fixes in fixes_by_file.values():
                        sorted_fix_results.extend(file_fixes)
                    
                    applied_this_pass = 0

                    for fix_result in sorted_fix_results:
                        fix_plan = fix_result["plan"]
                        source_failure = next(
                            (
                                item
                                for item in raw_failures_to_fix
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

                        failure_key = (fix_plan.file, fix_plan.line_number, fix_plan.bug_type)
                        
                        if applied:
                            applied_this_pass += 1
                            applied_in_iteration += 1
                            run_state["total_fixes_applied"] += 1
                            # Mark as successfully fixed so we don't retry
                            successfully_fixed.add(failure_key)
                        else:
                            # Track failed attempts to prevent infinite retry
                            if failure_key not in failed_attempts:
                                failed_attempts[failure_key] = 0
                            failed_attempts[failure_key] += 1

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

                # Deduplicate iteration_rows to keep only the latest attempt for each failure
                seen_failures: dict[tuple[str, str, int], dict] = {}
                for row in iteration_rows:
                    failure_key = (row["file"], row["bug_type"], row["line_number"])
                    # Keep the latest attempt (last one in the list)
                    seen_failures[failure_key] = row
                
                # Filter to only keep failures not already in fixes (avoid true duplicates)
                unique_iteration_rows = []
                for row in seen_failures.values():
                    # Check if this failure already exists in run_state["fixes"]
                    already_exists = any(
                        f["file"] == row["file"]
                        and f["bug_type"] == row["bug_type"]
                        and f["line_number"] == row["line_number"]
                        for f in run_state["fixes"]
                    )
                    if not already_exists:
                        unique_iteration_rows.append(row)

                if applied_in_iteration > 0:
                    committed, final_commit_message = self.github_ops.commit_changes(
                        repo_path=repo_dir,
                        commit_message=f"Iteration {iteration}: apply {applied_in_iteration} autonomous fixes",
                    )
                    if committed:
                        run_state["commit_count"] += 1
                        for row in unique_iteration_rows:
                            if row["status"] == "FIXED":
                                row["commit_message"] = final_commit_message

                run_state["fixes"].extend(unique_iteration_rows)

                # Push changes with error handling
                try:
                    self.github_ops.push_branch(repo_dir, branch_name)
                except Exception as push_error:
                    run_state["error_message"] = f"Push failed: {str(push_error)}"
                    print(f"Push error: {push_error}")
                    # Don't fail entirely, but mark that we couldn't push
                    
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
        
        # ✅ Cleanup Docker containers (sandboxed execution)
        if self.test_engine.executor:
            self.test_engine.executor.cleanup_all()

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
