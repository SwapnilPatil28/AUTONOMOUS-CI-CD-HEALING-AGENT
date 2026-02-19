from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


class StaticAnalyzerService:
    def analyze(self, repo_path: Path) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        for file_path in self._iter_python_files(repo_path):
            relative_path = file_path.relative_to(repo_path).as_posix()
            source = file_path.read_text(encoding="utf-8", errors="ignore")

            try:
                tree = ast.parse(source)
            except SyntaxError as error:
                failures.append(
                    {
                        "file": relative_path,
                        "line_number": error.lineno or 1,
                        "bug_type": "SYNTAX",
                        "message": error.msg or "SyntaxError",
                    }
                )
                failures.extend(self._find_unused_imports_in_source(source, relative_path))
                continue

            failures.extend(self._find_unused_imports(tree, relative_path))

        return failures

    def _iter_python_files(self, repo_path: Path):
        ignored_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
        }
        for file_path in repo_path.rglob("*.py"):
            if any(part in ignored_dirs for part in file_path.parts):
                continue
            yield file_path

    @staticmethod
    def _find_unused_imports(tree: ast.AST, relative_path: str) -> list[dict[str, Any]]:
        imported: dict[str, int] = {}
        used_names: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound_name = alias.asname or alias.name.split(".")[0]
                    if bound_name and not bound_name.startswith("_"):
                        imported[bound_name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    bound_name = alias.asname or alias.name
                    if bound_name and not bound_name.startswith("_"):
                        imported[bound_name] = node.lineno
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)

        failures: list[dict[str, Any]] = []
        for name, line in imported.items():
            if name not in used_names:
                failures.append(
                    {
                        "file": relative_path,
                        "line_number": line,
                        "bug_type": "LINTING",
                        "message": "unused import",
                    }
                )
        return failures

    @staticmethod
    def _find_unused_imports_in_source(source: str, relative_path: str) -> list[dict[str, Any]]:
        import_bindings: list[tuple[str, int]] = []
        lines = source.splitlines()

        for line_no, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not stripped.startswith(("import ", "from ")):
                continue
            if stripped.endswith("(") or stripped.endswith("\\"):
                continue

            try:
                import_tree = ast.parse(stripped)
            except SyntaxError:
                continue

            for node in ast.walk(import_tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        bound_name = alias.asname or alias.name.split(".")[0]
                        if bound_name and not bound_name.startswith("_"):
                            import_bindings.append((bound_name, line_no))
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "__future__":
                        continue
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        bound_name = alias.asname or alias.name
                        if bound_name and not bound_name.startswith("_"):
                            import_bindings.append((bound_name, line_no))

        if not import_bindings:
            return []

        source_without_comments = "\n".join(line.split("#", 1)[0] for line in lines)

        failures: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for name, line_no in import_bindings:
            occurrences = len(re.findall(rf"\b{re.escape(name)}\b", source_without_comments))
            if occurrences <= 1 and (name, line_no) not in seen:
                failures.append(
                    {
                        "file": relative_path,
                        "line_number": line_no,
                        "bug_type": "LINTING",
                        "message": "unused import",
                    }
                )
                seen.add((name, line_no))

        return failures