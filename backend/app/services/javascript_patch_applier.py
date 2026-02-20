"""JavaScript bug fixer - applies fixes for detected JavaScript bugs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class JavaScriptPatchApplierService:
    """Apply fixes for detected JavaScript bugs."""

    def apply_fixes(self, repo_path: Path, failures: list[dict[str, Any]]) -> dict[str, int]:
        """Apply all fixes to JavaScript files."""
        fixes_applied = 0
        files_modified = {}
        
        by_file = {}
        for failure in failures:
            file_path = failure["file"]
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(failure)
        
        for file_path_str, file_failures in by_file.items():
            file_path = repo_path / file_path_str
            if not file_path.exists():
                continue
            
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            original = source
            
            for failure in sorted(file_failures, key=lambda x: x["line_number"], reverse=True):
                bug_type = failure["bug_type"]
                line_num = failure["line_number"]
                msg = failure["message"]
                
                if bug_type == "SYNTAX":
                    source = self._fix_syntax(source, line_num, msg)
                elif bug_type == "LINTING":
                    source = self._fix_linting(source, line_num, msg)
                elif bug_type == "IMPORT":
                    source = self._fix_import(source, line_num, msg)
                elif bug_type == "LOGIC":
                    source = self._fix_logic(source, line_num, msg)
                elif bug_type == "TYPE_ERROR":
                    source = self._fix_type_error(source, line_num, msg)
                elif bug_type == "INDENTATION":
                    source = self._fix_indentation(source, line_num, msg)
                
                if source != original:
                    fixes_applied += 1
        
            if source != original:
                files_modified[file_path_str] = True
                file_path.write_text(source, encoding="utf-8")
        
        return {"fixed": fixes_applied, "files": len(files_modified)}

    def _fix_syntax(self, source: str, line_num: int, msg: str) -> str:
        """Fix SYNTAX errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        line = lines[line_num - 1]
        
        # Missing semicolon
        if "semicolon" in msg.lower():
            if not line.rstrip().endswith((";", "{", "}")):
                lines[line_num - 1] = line.rstrip() + ";"

        if "closing parenthesis" in msg.lower() and not line.rstrip().endswith(")"):
            lines[line_num - 1] = line.rstrip() + ")"

        if "closing bracket" in msg.lower() and not line.rstrip().endswith("]"):
            lines[line_num - 1] = line.rstrip() + "]"
        
        return "\n".join(lines)

    def _fix_linting(self, source: str, line_num: int, msg: str) -> str:
        """Fix LINTING errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        line = lines[line_num - 1]
        
        # Remove unused import
        if "unused import" in msg.lower():
            lines[line_num - 1] = ""
        
        # Fix snake_case to camelCase
        if "camelcase" in msg.lower() and "snake_case" in msg.lower():
            match = re.search(r"Variable '(\w+)'", msg)
            if match:
                var_name = match.group(1)
                camel_case = self._to_camel_case(var_name)
                lines[line_num - 1] = line.replace(var_name, camel_case)

        # Fix parameter name to camelCase
        if "parameter name should be camelcase" in msg.lower():
            match = re.search(r"'([a-zA-Z_]\w*)'", msg)
            if match:
                var_name = match.group(1)
                camel_case = self._to_camel_case(var_name)
                lines[line_num - 1] = line.replace(var_name, camel_case)
        
        # Fix class name to PascalCase
        if "PascalCase" in msg and "class" in msg.lower():
            match = re.search(r"Class '(\w+)'", msg)
            if match:
                old_name = match.group(1)
                new_name = old_name[0].upper() + old_name[1:] if old_name else old_name
                lines[line_num - 1] = line.replace(f"class {old_name}", f"class {new_name}")
                source = "\n".join(lines)
                source = source.replace(f" {old_name} ", f" {new_name} ")
                source = source.replace(f"new {old_name}", f"new {new_name}")
                lines = source.split("\n")

        if "unused variable" in msg.lower():
            if re.match(r"^\s*(let|const|var)\s+\w+\s*(=|;)\s*", line):
                lines[line_num - 1] = ""
        
        return "\n".join(lines)

    def _fix_import(self, source: str, line_num: int, msg: str) -> str:
        """Fix IMPORT errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        # Remove imports after code
        if "after code" in msg.lower():
            lines[line_num - 1] = ""

        if "incomplete import" in msg.lower():
            lines[line_num - 1] = ""
        
        return "\n".join(lines)

    def _fix_logic(self, source: str, line_num: int, msg: str) -> str:
        """Fix LOGIC errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        line = lines[line_num - 1]
        
        # Fix += to -=
        if "removal operation" in msg.lower() and "+=" in line:
            lines[line_num - 1] = line.replace("+=", "-=")
        
        # Fix -= to +=
        if "addition operation" in msg.lower() and "-=" in line:
            lines[line_num - 1] = line.replace("-=", "+=")
        
        # Fix divisor
        if "divisor" in msg.lower() and "/" in line:
            iterable = self._infer_iterable_name(lines, line_num)
            if iterable:
                lines[line_num - 1] = re.sub(r"/\s*(\d+)", f"/ {iterable}.length", line)

        if "xor" in msg.lower() or "exponentiation" in msg.lower():
            lines[line_num - 1] = re.sub(r"\b(\w+)\s*\^\s*(\w+)\b", r"\1 ** \2", line, count=1)

        if "string literal" in msg.lower():
            lines[line_num - 1] = re.sub(r'([+\-*/])\s*["\"]([a-zA-Z_]\w*)["\"]', r"\1 \2", line, count=1)

        if "comparison for max uses '<'" in msg.lower() and "<" in line:
            lines[line_num - 1] = line.replace("<", ">", 1)
        if "comparison for min uses '>'" in msg.lower() and ">" in line:
            lines[line_num - 1] = line.replace(">", "<", 1)

        if "return inside accumulation loop" in msg.lower() and line.lstrip().startswith("return"):
            for prev_idx in range(line_num - 2, -1, -1):
                prev_line = lines[prev_idx]
                if re.search(r"\bfor\b|\bwhile\b", prev_line):
                    base_indent = len(prev_line) - len(prev_line.lstrip())
                    lines[line_num - 1] = (" " * base_indent) + line.lstrip()
                    break

        if "min/max tracker initialized to constant" in msg.lower():
            assign_match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*-?\d+(?:\.\d+)?\s*;\s*$", line)
            if assign_match:
                indent, var_name = assign_match.group(1), assign_match.group(2)
                iterable = self._infer_iterable_name(lines, line_num)
                if iterable:
                    lines[line_num - 1] = f"{indent}{var_name} = {iterable}[0];"

        if "threshold tracker initialized too high" in msg.lower():
            assign_match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*-?\d+(?:\.\d+)?\s*;\s*$", line)
            if assign_match:
                indent, var_name = assign_match.group(1), assign_match.group(2)
                lines[line_num - 1] = f"{indent}{var_name} = Number.NEGATIVE_INFINITY;"

        if "threshold tracker initialized too low" in msg.lower():
            assign_match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*-?\d+(?:\.\d+)?\s*;\s*$", line)
            if assign_match:
                indent, var_name = assign_match.group(1), assign_match.group(2)
                lines[line_num - 1] = f"{indent}{var_name} = Number.POSITIVE_INFINITY;"
        
        return "\n".join(lines)

    def _fix_type_error(self, source: str, line_num: int, msg: str) -> str:
        """Fix TYPE_ERROR errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        line = lines[line_num - 1]
        
        # Add String conversion for concatenation
        if "string concatenation" in msg.lower() or "type mismatch" in msg.lower():
            match = re.search(r'["\'].*["\']\s*\+\s*(\w+)', line)
            if match:
                var = match.group(1)
                lines[line_num - 1] = line.replace(f"+ {var}", f"+ String({var})")

        if "mixed numeric and string values in collection" in msg.lower():
            lines[line_num - 1] = re.sub(r'"\s*(-?\d+(?:\.\d+)?)\s*"', r"\1", line)
        
        return "\n".join(lines)

    def _fix_indentation(self, source: str, line_num: int, msg: str) -> str:
        """Fix INDENTATION errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        lines[line_num - 1] = "  " + lines[line_num - 1]
        
        return "\n".join(lines)

    @staticmethod
    def _infer_iterable_name(lines: list[str], line_num: int) -> str | None:
        for prev_idx in range(line_num - 2, -1, -1):
            prev = lines[prev_idx]
            for_of = re.search(r"for\s*\(\s*(?:const|let|var)\s+\w+\s+of\s+(\w+)\s*\)", prev)
            if for_of:
                return for_of.group(1)
            index_for = re.search(r"for\s*\(.*;\s*\w+\s*<\s*(\w+)\.length\s*;", prev)
            if index_for:
                return index_for.group(1)
        return None

    @staticmethod
    def _to_camel_case(snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])
