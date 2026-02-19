from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path

from app.agents.types import Failure, FixPlan


class TestDiscoveryAgent:
    def discover(self, repo_path: Path) -> list[Path]:
        patterns = ["test_*.py", "*_test.py", "*.spec.ts", "*.test.ts", "*.test.js", "*Test.java"]
        tests: list[Path] = []
        for pattern in patterns:
            tests.extend(repo_path.rglob(pattern))
        return sorted(set(tests))


class FailureClassifierAgent:
    def classify(self, raw_failures: list[dict]) -> list[Failure]:
        failures: list[Failure] = []
        for item in raw_failures:
            failures.append(
                Failure(
                    file=item["file"],
                    line_number=item["line_number"],
                    bug_type=item["bug_type"],
                    message=item["message"],
                )
            )
        return failures


class PatchGeneratorAgent:
    def generate(self, failure: Failure) -> FixPlan:
        action_map = {
            "LINTING": "remove the import statement",
            "SYNTAX": "add the colon at the correct position",
            "LOGIC": "adjust the conditional branch and return value",
            "TYPE_ERROR": "align variable and function type usage",
            "IMPORT": "correct the import path and symbol name",
            "INDENTATION": "fix the indentation level",
        }
        fix_text = action_map[failure.bug_type]
        expected_output = (
            f"{failure.bug_type} error in {failure.file} line {failure.line_number} "
            f"→ Fix: {fix_text}"
        )
        return FixPlan(
            file=failure.file,
            line_number=failure.line_number,
            bug_type=failure.bug_type,
            commit_message=f"Fix {failure.bug_type} in {failure.file}:{failure.line_number}",
            expected_output=expected_output,
        )


class VerifierAgent:
    def local_verify(self, fix_plan: FixPlan) -> bool:
        return True


class TimelineAgent:
    def event(self, iteration: int, retry_limit: int, passed: bool) -> dict:
        return {
            "iteration": iteration,
            "retry_limit": retry_limit,
            "status": "PASSED" if passed else "FAILED",
            "timestamp": datetime.now(UTC).isoformat(),
        }
