from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from git import Repo

from app.core.policy import ensure_commit_prefix


class GitHubOpsService:
    def __init__(self) -> None:
        self.github_token = os.getenv("GITHUB_TOKEN", "").strip()

    def _inject_token(self, repo_url: str) -> str:
        if not self.github_token:
            return repo_url
        if repo_url.startswith("https://"):
            return repo_url.replace("https://", f"https://x-access-token:{self.github_token}@")
        return repo_url

    def parse_owner_repo(self, repo_url: str) -> tuple[str, str]:
        parsed = urlparse(repo_url)
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        parts = [part for part in path.split("/") if part]
        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        return parts[0], parts[1]

    def clone_repository(self, repo_url: str, target_path: Path) -> Path:
        if target_path.exists():
            return target_path
        auth_url = self._inject_token(repo_url)
        Repo.clone_from(auth_url, target_path)
        return target_path

    def create_branch(self, repo_path: Path, branch_name: str, base_branch: str = "main") -> str:
        repo = Repo(repo_path)
        remote = repo.remote("origin")
        remote.fetch()

        base_ref = None
        for candidate in [f"origin/{base_branch}", "origin/main", "origin/master"]:
            if candidate in [str(ref) for ref in repo.refs]:
                base_ref = candidate
                break

        if base_ref is None:
            if repo.head.is_valid():
                base_ref = str(repo.head.reference)
            else:
                raise RuntimeError("Unable to resolve base branch for new branch creation.")

        existing = [head.name for head in repo.heads]
        if branch_name in existing:
            repo.git.checkout(branch_name)
        else:
            repo.git.checkout("-b", branch_name, base_ref)
        return branch_name

    def commit_fix(self, repo_path: Path, commit_message: str) -> str:
        committed, final_message = self.commit_changes(repo_path, commit_message)
        return final_message

    def commit_changes(self, repo_path: Path, commit_message: str) -> tuple[bool, str]:
        repo = Repo(repo_path)
        final_message = ensure_commit_prefix(commit_message)
        repo.git.add(A=True)
        if not repo.is_dirty(untracked_files=True):
            return False, final_message
        repo.index.commit(final_message)
        return True, final_message

    def push_branch(self, repo_path: Path, branch_name: str) -> None:
        repo = Repo(repo_path)
        if repo.active_branch.name.lower() == "main":
            raise RuntimeError("Refusing to push directly to main branch.")
        repo.remote("origin").push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)

    async def _latest_workflow_run(self, owner: str, repo: str, branch_name: str) -> dict | None:
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=headers, params={"branch": branch_name, "per_page": 10})
            response.raise_for_status()
            payload = response.json()

        runs = payload.get("workflow_runs", [])
        if not runs:
            return None
        return runs[0]

    async def poll_ci_status(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        timeout_seconds: int = 480,
    ) -> tuple[str, str | None]:
        elapsed = 0
        workflow_url = None
        while elapsed < timeout_seconds:
            run = await self._latest_workflow_run(owner, repo, branch_name)
            if run is not None:
                workflow_url = run.get("html_url")
                status = run.get("status")
                conclusion = run.get("conclusion")

                if status == "completed":
                    if conclusion == "success":
                        return "PASSED", workflow_url
                    return "FAILED", workflow_url

            await asyncio.sleep(8)
            elapsed += 8

        return "FAILED", workflow_url
