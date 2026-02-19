from __future__ import annotations

import re
from pathlib import Path


class PatchApplierService:
    def apply_fix(self, repo_path: Path, file_path: str, line_number: int, bug_type: str, message: str) -> bool:
        target = repo_path / file_path
        if not target.exists() or target.is_dir():
            return False

        lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line_number < 1 or line_number > len(lines):
            return False

        index = line_number - 1
        original = lines[index]
        changed = False

        if bug_type in {"LINTING", "IMPORT"}:
            line_lower = original.lower()
            msg_lower = message.lower()
            if self._is_safe_import_line(original) and (
                "unused import" in msg_lower
                or "imported but unused" in msg_lower
                or "f401" in msg_lower
                or "unused import" in line_lower
            ):
                lines.pop(index)
                changed = True
        elif bug_type == "SYNTAX":
            code_part, comment_part = self._split_inline_comment(original)
            if code_part and not code_part.endswith(":") and re.search(
                r"\b(if|elif|for|while|def|class|else|try|except|with)\b",
                code_part,
            ):
                if comment_part:
                    lines[index] = f"{code_part}: {comment_part}"
                else:
                    lines[index] = f"{code_part}:"
                changed = True
        elif bug_type == "INDENTATION":
            replaced = original.replace("\t", "    ")
            if replaced != original:
                lines[index] = replaced
                changed = True

        if changed:
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return changed

    @staticmethod
    def _split_inline_comment(line: str) -> tuple[str, str]:
        if "#" not in line:
            return line.rstrip(), ""
        hash_index = line.index("#")
        code_part = line[:hash_index].rstrip()
        comment_part = line[hash_index:].lstrip()
        return code_part, comment_part

    @staticmethod
    def _is_safe_import_line(line: str) -> bool:
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            return False
        if stripped.endswith("(") or stripped.endswith("\\"):
            return False
        return True
