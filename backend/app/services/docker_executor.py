from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ContainerExecResult:
    container_id: str
    return_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


class DockerExecutor:
    """
    Sandboxed code execution using Docker containers.
    Ensures repository code runs isolated from host system.
    """

    def __init__(self, image: str = "python:3.12-slim"):
        self.image = image
        self.containers: list[str] = []

    def create_container(self, work_dir: Path, name: str | None = None) -> str:
        """Create and start a Docker container for sandboxed execution."""
        cmd = [
            "docker",
            "create",
            "-it",
            "--rm",
            "-v", f"{work_dir}:/workspace",
            "-w", "/workspace",
            "--name", name or f"sandbox-{id(work_dir)}",
            self.image,
            "sleep", "infinity",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()
            
            # Start the container
            subprocess.run(["docker", "start", container_id], check=True, capture_output=True)
            self.containers.append(container_id)
            return container_id
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create Docker container: {e.stderr}")

    def execute_in_container(self, container_id: str, command: list[str], timeout: int = 240) -> ContainerExecResult:
        """Execute a command inside a Docker container."""
        docker_cmd = ["docker", "exec", container_id] + command
        try:
            process = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return ContainerExecResult(
                container_id=container_id,
                return_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
            )
        except subprocess.TimeoutExpired:
            return ContainerExecResult(
                container_id=container_id,
                return_code=124,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
            )
        except subprocess.CalledProcessError as e:
            return ContainerExecResult(
                container_id=container_id,
                return_code=e.returncode,
                stdout=e.stdout or "",
                stderr=e.stderr or str(e),
            )

    def copy_to_container(self, container_id: str, src: Path, dest: str) -> None:
        """Copy a file or directory into the container."""
        cmd = ["docker", "cp", str(src), f"{container_id}:{dest}"]
        subprocess.run(cmd, check=True, capture_output=True)

    def copy_from_container(self, container_id: str, src: str, dest: Path) -> None:
        """Copy a file or directory from the container."""
        cmd = ["docker", "cp", f"{container_id}:{src}", str(dest)]
        subprocess.run(cmd, check=True, capture_output=True)

    def stop_container(self, container_id: str) -> None:
        """Stop and remove a Docker container."""
        try:
            subprocess.run(["docker", "stop", container_id], capture_output=True)
            subprocess.run(["docker", "rm", container_id], capture_output=True)
            if container_id in self.containers:
                self.containers.remove(container_id)
        except Exception:
            pass

    def cleanup_all(self) -> None:
        """Stop and remove all tracked containers."""
        for container_id in self.containers[:]:
            self.stop_container(container_id)

    def healthcheck(self) -> bool:
        """Check if Docker is available and working."""
        try:
            result = subprocess.run(["docker", "version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
