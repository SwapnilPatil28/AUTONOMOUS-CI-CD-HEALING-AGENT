from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.docker_executor import DockerExecutor, ContainerExecResult


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
    def __init__(self, use_docker: bool = True):
        """
        Initialize test engine.
        
        Args:
            use_docker: If True, runs tests in Docker containers (RECOMMENDED for security).
                       If False, runs tests directly on host (only for local development).
        """
        self.use_docker = use_docker
        self.executor = DockerExecutor() if use_docker else None

    def detect_command(self, repo_path: Path) -> list[str]:
        """Detect the test command based on project structure."""
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
        """
        Run tests in sandboxed Docker container (RECOMMENDED) or directly on host.
        
        IMPORTANT: Docker execution provides security isolation:
        - Tests run in isolated container
        - No access to host filesystem (except /workspace mount)
        - No network access unless configured
        - Automatic cleanup after execution
        """
        command = self.detect_command(repo_path)
        
        if self.use_docker and self.executor and self.executor.healthcheck():
            return self._run_tests_in_docker(repo_path, command, timeout_seconds)
        else:
            # Fallback to direct execution if Docker unavailable
            return self._run_tests_directly(repo_path, command, timeout_seconds)

    def _run_tests_in_docker(self, repo_path: Path, command: list[str], timeout_seconds: int) -> TestRunResult:
        """Execute tests in a Docker container (SANDBOXED)."""
        container_id = None
        try:
            container_id = self.executor.create_container(repo_path)
            
            # Install dependencies if needed
            if "pytest" in command:
                self.executor.execute_in_container(container_id, ["pip", "install", "-q", "pytest"])
            elif "npm" in command:
                self.executor.execute_in_container(container_id, ["npm", "install", "--silent"])
            
            # Run tests
            result: ContainerExecResult = self.executor.execute_in_container(
                container_id,
                command,
                timeout=timeout_seconds
            )
            
            return TestRunResult(
                command=command,
                return_code=result.return_code,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        finally:
            if container_id:
                self.executor.stop_container(container_id)

    def _run_tests_directly(self, repo_path: Path, command: list[str], timeout_seconds: int) -> TestRunResult:
        """Execute tests directly on host (NOT SANDBOXED - use only for development)."""
        import subprocess
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
