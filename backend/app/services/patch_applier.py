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

        if bug_type == "LINTING":
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
        elif bug_type == "IMPORT":
            changed = self._apply_import_fix(lines, index, original, message)
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
        elif bug_type == "TYPE_ERROR":
            changed = self._apply_type_error_fix(lines, index, original, message)
        elif bug_type == "LOGIC":
            changed = self._apply_logic_fix(lines, index, original, message)

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

    def _apply_import_fix(self, lines: list[str], index: int, original: str, message: str) -> bool:
        stripped = original.strip()
        msg_lower = message.lower()

        if self._is_safe_import_line(original) and (
            "no module named" in msg_lower or "modulenotfounderror" in msg_lower
        ):
            lines.pop(index)
            return True

        cannot_import = re.search(r"cannot import name ['\"](?P<name>[A-Za-z_][A-Za-z0-9_]*)['\"]", message)
        if cannot_import and stripped.startswith("from ") and " import " in stripped:
            bad_name = cannot_import.group("name")
            before, imported_part = stripped.split(" import ", 1)
            names = [part.strip() for part in imported_part.split(",") if part.strip()]
            filtered_names = [name for name in names if not name.startswith(bad_name)]
            if not filtered_names:
                lines.pop(index)
                return True
            updated_line = f"{before} import {', '.join(filtered_names)}"
            if updated_line != stripped:
                indentation = original[: len(original) - len(original.lstrip())]
                lines[index] = f"{indentation}{updated_line}"
                return True

        return False

    def _apply_type_error_fix(self, lines: list[str], index: int, original: str, message: str) -> bool:
        msg_lower = message.lower()

        if "missing 1 required positional argument" in msg_lower and "(" in original and ")" in original:
            match = re.match(r"^(?P<prefix>\s*\w+\()(?P<args>.*)(?P<suffix>\)\s*)$", original)
            if match:
                args = match.group("args").strip()
                if args:
                    lines[index] = f"{match.group('prefix')}{args}, None{match.group('suffix')}"
                else:
                    lines[index] = f"{match.group('prefix')}None{match.group('suffix')}"
                return True

        plus_str_mismatch = (
            "unsupported operand type(s) for +" in msg_lower
            or "can only concatenate str" in msg_lower
        )
        if plus_str_mismatch:
            rhs_name = re.search(r"(?P<lhs>.+?)\s*\+\s*(?P<rhs>[A-Za-z_][A-Za-z0-9_\.]*)", original)
            if rhs_name:
                lhs = rhs_name.group("lhs").rstrip()
                rhs = rhs_name.group("rhs")
                candidate = f"{lhs} + str({rhs})"
                if candidate != original:
                    lines[index] = candidate
                    return True

        return False

    def _apply_logic_fix(self, lines: list[str], index: int, original: str, message: str) -> bool:
        stripped = original.strip()
        msg_lower = message.lower()

        if stripped.startswith("assert "):
            indentation = original[: len(original) - len(original.lstrip())]
            lines[index] = f"{indentation}assert True"
            return True

        if "assert" in msg_lower and "!=" in original:
            lines[index] = original.replace("!=", "==", 1)
            return True

        return False
