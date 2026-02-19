from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestRunResult:
    command: list[str]
    return_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


class TestEngineService:
    def detect_command(self, repo_path: Path) -> list[str]:
        if (repo_path / "pytest.ini").exists() or (repo_path / "pyproject.toml").exists() or any(repo_path.rglob("test_*.py")):
            return ["python", "-m", "pytest", "-q"]
        if (repo_path / "package.json").exists():
            return ["npm", "test", "--", "--watch=false"]
        if (repo_path / "pom.xml").exists():
            return ["mvn", "-B", "test"]
        if (repo_path / "build.gradle").exists() or (repo_path / "build.gradle.kts").exists():
            return ["gradle", "test"]
        if any(repo_path.glob("*.sln")) or any(repo_path.rglob("*.csproj")):
            return ["dotnet", "test"]
        return ["python", "-m", "pytest", "-q"]

    def run_tests(self, repo_path: Path, timeout_seconds: int = 240) -> TestRunResult:
        command = self.detect_command(repo_path)
        process = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return TestRunResult(
            command=command,
            return_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )
