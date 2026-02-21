"""Java bug fixer - applies fixes for detected Java bugs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class JavaPatchApplierService:
    """Apply fixes for detected Java bugs."""

    def apply_fixes(self, repo_path: Path, failures: list[dict[str, Any]]) -> dict[str, int]:
        """Apply all fixes to Java files. Returns count of fixes applied."""
        fixes_applied = 0
        files_modified = {}
        
        # Group failures by file
        by_file = {}
        for failure in failures:
            file_path = failure["file"]
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(failure)
        
        # Apply fixes file by file
        for file_path_str, file_failures in by_file.items():
            file_path = repo_path / file_path_str
            if not file_path.exists():
                continue
            
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            original = source
            
            # Sort by line number (descending) to avoid offset issues
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

        # Constructor name mismatch with class name
        if "constructor name does not match class name" in msg.lower():
            class_match = re.search(r"\bclass\s+([A-Za-z_]\w*)", source)
            ctor_match = re.match(r"^(\s*(?:public|private|protected)\s+)([A-Za-z_]\w*)(\s*\([^)]*\)\s*\{?\s*)$", line)
            if class_match and ctor_match:
                lines[line_num - 1] = f"{ctor_match.group(1)}{class_match.group(1)}{ctor_match.group(3)}"
        
        # Missing brace
        if "brace" in msg.lower():
            lines[line_num - 1] = line.rstrip() + " {"

        # Missing closing parenthesis
        if "closing parenthesis" in msg.lower() and not line.rstrip().endswith(")"):
            lines[line_num - 1] = line.rstrip() + ")"

        # Missing closing bracket
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
            # Mark line for removal
            lines[line_num - 1] = ""

        if "scanner type should be capitalized" in msg.lower():
            source = "\n".join(lines)
            source = re.sub(r"\bjava\.util\.scanner\b", "java.util.Scanner", source)
            source = re.sub(r"\bscanner\b", "Scanner", source)
            lines = source.split("\n")
        
        # Fix snake_case to camelCase
        if "camelcase" in msg.lower() and "snake_case" in msg.lower():
            # Extract variable name
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
                parts = [part for part in re.split(r"[_\s]+", old_name) if part]
                new_name = "".join(part[:1].upper() + part[1:] for part in parts) if parts else (old_name[:1].upper() + old_name[1:])
                lines[line_num - 1] = line.replace(f"class {old_name}", f"class {new_name}")
                # Update all references
                source = "\n".join(lines)
                source = source.replace(f" {old_name} ", f" {new_name} ")
                source = source.replace(f"new {old_name}(", f"new {new_name}(")
                lines = source.split("\n")

        # Fix method name to camelCase
        if "method name should be camelcase" in msg.lower():
            match = re.search(r"'([A-Za-z_][A-Za-z0-9_]*)'", msg)
            if match:
                old_name = match.group(1)
                if "_" not in old_name:
                    return "\n".join(lines)
                parts = [part for part in re.split(r"[_\s]+", old_name) if part]
                if parts:
                    camel = parts[0][:1].lower() + parts[0][1:]
                    camel += "".join(part[:1].upper() + part[1:] for part in parts[1:])
                else:
                    camel = old_name[:1].lower() + old_name[1:]
                if camel != old_name:
                    source = "\n".join(lines)
                    source = re.sub(rf"\b{re.escape(old_name)}\b(?=\s*\()", camel, source)
                    source = re.sub(
                        rf"(\b[A-Za-z_][\w<>\[\]]*\s+){re.escape(old_name)}(?=\s*\([^)]*\)\s*\{{)",
                        rf"\1{camel}",
                        source,
                    )
                    lines[:] = source.split("\n")

        # Remove unused variable assignment
        if "unused variable" in msg.lower():
            if re.match(r"^\s*\w[\w<>\[\]]*\s+\w+\s*(=|;)\s*", line):
                lines[line_num - 1] = ""
        
        return "\n".join(lines)

    def _fix_import(self, source: str, line_num: int, msg: str) -> str:
        """Fix IMPORT errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        # For imports after code, remove them
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

        if "loop bound exceeds array dimension" in msg.lower():
            source = self._fix_array_loop_bound(source, line_num)
            lines = source.split("\n")
            line = lines[line_num - 1] if line_num <= len(lines) else line
        
        # Fix += to -=  for removal
        if "removal operation" in msg.lower() and "+=" in line:
            lines[line_num - 1] = line.replace("+=", "-=")
        
        # Fix -= to += for addition
        if "addition operation" in msg.lower() and "-=" in line:
            lines[line_num - 1] = line.replace("-=", "+=")
        
        # Fix divisor for average
        if "divisor" in msg.lower() and "/" in line:
            # Replace /constant with /.length
            iterable_name = self._infer_iterable_name(lines, line_num)
            if iterable_name:
                replacement = f"{iterable_name}.size()" if iterable_name.endswith("List") or "list" in iterable_name.lower() else f"{iterable_name}.length"
                lines[line_num - 1] = re.sub(r"/\s*(\d+)", f"/ {replacement}", line)

        # Fix XOR to exponentiation using Math.pow
        if "xor" in msg.lower() or "exponentiation" in msg.lower():
            xor_match = re.search(r"(\w+)\s*\^\s*(\w+)", line)
            if xor_match:
                left = xor_match.group(1)
                right = xor_match.group(2)
                lines[line_num - 1] = re.sub(r"\b\w+\s*\^\s*\w+\b", f"Math.pow({left}, {right})", line, count=1)

        # Fix string literal used instead of variable
        if "string literal" in msg.lower():
            lines[line_num - 1] = re.sub(r'([+\-*/])\s*["\"]([a-zA-Z_]\w*)["\"]', r"\1 \2", line, count=1)

        # Fix reversed comparisons for max/min
        if "comparison for max uses '<'" in msg.lower() and "<" in line:
            lines[line_num - 1] = line.replace("<", ">", 1)
        if "comparison for min uses '>'" in msg.lower() and ">" in line:
            lines[line_num - 1] = line.replace(">", "<", 1)

        # Fix return inside accumulation loop by dedenting
        if "return inside accumulation loop" in msg.lower():
            if line.lstrip().startswith("return"):
                for prev_idx in range(line_num - 2, -1, -1):
                    prev_line = lines[prev_idx]
                    if re.search(r"\bfor\b|\bwhile\b", prev_line):
                        base_indent = len(prev_line) - len(prev_line.lstrip())
                        lines[line_num - 1] = (" " * base_indent) + line.lstrip()
                        break

        # Fix min/max tracker initialized to constant
        if "min/max tracker initialized to constant" in msg.lower():
            assign_match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*-?\d+(?:\.\d+)?\s*;\s*$", line)
            if assign_match:
                indent, var_name = assign_match.group(1), assign_match.group(2)
                iterable = self._infer_iterable_name(lines, line_num)
                if iterable:
                    accessor = f"{iterable}.get(0)" if iterable.endswith("List") or "list" in iterable.lower() else f"{iterable}[0]"
                    lines[line_num - 1] = f"{indent}{var_name} = {accessor};"

        if "threshold tracker initialized too high" in msg.lower():
            assign_match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*-?\d+(?:\.\d+)?\s*;\s*$", line)
            if assign_match:
                indent, var_name = assign_match.group(1), assign_match.group(2)
                lines[line_num - 1] = f"{indent}{var_name} = Double.NEGATIVE_INFINITY;"

        if "threshold tracker initialized too low" in msg.lower():
            assign_match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*-?\d+(?:\.\d+)?\s*;\s*$", line)
            if assign_match:
                indent, var_name = assign_match.group(1), assign_match.group(2)
                lines[line_num - 1] = f"{indent}{var_name} = Double.POSITIVE_INFINITY;"

        if "isboardfull returns true when empty slot found" in msg.lower():
            # Flip immediate return true -> false in method block
            method_end = self._find_method_end(lines, line_num - 1)
            for idx in range(line_num - 1, method_end):
                if re.search(r"\breturn\s+true\s*;", lines[idx]):
                    lines[idx] = re.sub(r"\breturn\s+true\s*;", "return false;", lines[idx], count=1)
                    break

            # Flip trailing return false -> true in method block
            for idx in range(method_end - 1, line_num - 2, -1):
                if re.search(r"\breturn\s+false\s*;", lines[idx]):
                    lines[idx] = re.sub(r"\breturn\s+false\s*;", "return true;", lines[idx], count=1)
                    break

        if "checkwin missing column and/or diagonal checks" in msg.lower():
            method_end = self._find_method_end(lines, line_num - 1)
            insert_at = None
            for idx in range(method_end - 1, line_num - 2, -1):
                if re.search(r"\breturn\s+false\s*;", lines[idx]):
                    insert_at = idx
                    break
            if insert_at is not None:
                indent = re.match(r"^(\s*)", lines[insert_at]).group(1)
                extra = [
                    f"{indent}for (int i = 0; i < 3; i++) {{",
                    f"{indent}    if (board[0][i] == player && board[1][i] == player && board[2][i] == player) {{",
                    f"{indent}        return true;",
                    f"{indent}    }}",
                    f"{indent}}}",
                    "",
                    f"{indent}if (board[0][0] == player && board[1][1] == player && board[2][2] == player) {{",
                    f"{indent}    return true;",
                    f"{indent}}}",
                    f"{indent}if (board[0][2] == player && board[1][1] == player && board[2][0] == player) {{",
                    f"{indent}    return true;",
                    f"{indent}}}",
                ]
                lines[insert_at:insert_at] = extra

        if "missing tie-check in loop when board is full" in msg.lower():
            while_idx = line_num - 1
            insert_idx = None
            for idx in range(while_idx + 1, min(len(lines), while_idx + 80)):
                if re.search(r"player\s*=\s*\(.*\?\s*'O'\s*:\s*'X'\s*\)", lines[idx]):
                    insert_idx = idx
                    break
            if insert_idx is None:
                for idx in range(while_idx + 1, min(len(lines), while_idx + 80)):
                    if re.search(r"\}\s*else\s*\{", lines[idx]):
                        insert_idx = idx
                        break
            if insert_idx is not None:
                base_indent = re.match(r"^(\s*)", lines[insert_idx]).group(1)
                obj = "game"
                for probe in range(max(0, while_idx - 20), min(len(lines), while_idx + 40)):
                    m = re.search(r"\b([A-Za-z_]\w*)\.printBoard\s*\(", lines[probe])
                    if m:
                        obj = m.group(1)
                        break
                tie_block = [
                    f"{base_indent}if ({obj}.isBoardFull()) {{",
                    f"{base_indent}    {obj}.printBoard();",
                    f"{base_indent}    System.out.println(\"Game is a tie!\");",
                    f"{base_indent}    break;",
                    f"{base_indent}}}",
                ]
                lines[insert_idx:insert_idx] = tie_block
        
        return "\n".join(lines)

    @staticmethod
    def _infer_iterable_name(lines: list[str], line_num: int) -> str | None:
        for prev_idx in range(line_num - 2, -1, -1):
            prev = lines[prev_idx]
            enhanced_for = re.search(r"for\s*\(\s*\w[\w<>\[\]]*\s+\w+\s*:\s*(\w+)\s*\)", prev)
            if enhanced_for:
                return enhanced_for.group(1)
            index_for = re.search(r"for\s*\(.*;\s*\w+\s*<\s*(\w+)\.length\s*;", prev)
            if index_for:
                return index_for.group(1)
        return None

    def _fix_type_error(self, source: str, line_num: int, msg: str) -> str:
        """Fix TYPE_ERROR errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source
        
        line = lines[line_num - 1]
        
        # Add conversion for concatenation
        if "string concatenation" in msg.lower() or "type mismatch" in msg.lower():
            match = re.search(r'".*"\s*\+\s*(\w+(?:\.\w+)?)', line)
            if match:
                var = match.group(1)
                lines[line_num - 1] = line.replace(f"+ {var}", f"+ String.valueOf({var})")

        if "char assigned from string literal" in msg.lower():
            lines[line_num - 1] = re.sub(r'\"(.?)\"', lambda m: f"'{m.group(1)}'", line)

        if "int assigned from scanner.next()" in msg.lower():
            lines[line_num - 1] = re.sub(r"\.next\s*\(\s*\)", ".nextInt()", lines[line_num - 1])

        if "scanner type should be capitalized" in msg.lower():
            source = "\n".join(lines)
            source = re.sub(r"\bjava\.util\.scanner\b", "java.util.Scanner", source)
            source = re.sub(r"\bscanner\b", "Scanner", source)
            lines = source.split("\n")

        # Fix numeric assignment from string literal
        if "assigned string literal to numeric type" in msg.lower():
            lines[line_num - 1] = re.sub(r'"(-?\d+(?:\.\d+)?)"', r"\1", line)

        # Fix mixed numeric/string collection literal
        if "mixed numeric and string values in collection" in msg.lower():
            lines[line_num - 1] = re.sub(r'"\s*(-?\d+(?:\.\d+)?)\s*"', r"\1", line)
        
        return "\n".join(lines)

    def _fix_indentation(self, source: str, line_num: int, msg: str) -> str:
        """Fix INDENTATION errors."""
        lines = source.split("\n")
        if line_num > len(lines):
            return source

        stripped = lines[line_num - 1].lstrip()
        depth = 0
        for idx in range(0, line_num - 1):
            segment = lines[idx]
            depth += segment.count("{")
            depth -= segment.count("}")
            if depth < 0:
                depth = 0

        if stripped.startswith("}"):
            depth = max(0, depth - 1)

        lines[line_num - 1] = (" " * (depth * 4)) + stripped
        
        return "\n".join(lines)

    @staticmethod
    def _to_camel_case(snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @staticmethod
    def _find_method_end(lines: list[str], start_idx: int) -> int:
        depth = 0
        seen_open = False
        for idx in range(start_idx, len(lines)):
            line = lines[idx]
            depth += line.count("{")
            if line.count("{") > 0:
                seen_open = True
            depth -= line.count("}")
            if seen_open and depth <= 0:
                return idx + 1
        return len(lines)

    def _fix_array_loop_bound(self, source: str, line_num: int) -> str:
        lines = source.split("\n")
        if line_num > len(lines):
            return source

        array_dims: dict[str, tuple[int, int]] = {}
        for line in lines:
            arr_decl = re.search(r"\b\w+\s*\[\]\s*\[\]\s*([A-Za-z_]\w*)\s*=\s*new\s+\w+\[(\d+)\]\[(\d+)\]", line)
            if arr_decl:
                array_dims[arr_decl.group(1)] = (int(arr_decl.group(2)), int(arr_decl.group(3)))

        access_idx = line_num - 1
        access = re.search(r"\b([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*)\s*\]\s*\[\s*([A-Za-z_]\w*)\s*\]", lines[access_idx])
        if not access:
            return source

        arr_name, idx1, idx2 = access.group(1), access.group(2), access.group(3)
        if arr_name not in array_dims:
            return source
        dim1, dim2 = array_dims[arr_name]

        for back in range(access_idx, max(-1, access_idx - 12), -1):
            loop_match = re.search(r"for\s*\(\s*int\s+([A-Za-z_]\w*)\s*=\s*0\s*;\s*\1\s*<\s*(\d+)\s*;", lines[back])
            if not loop_match:
                continue
            loop_var = loop_match.group(1)
            current_bound = int(loop_match.group(2))
            if loop_var == idx1:
                if current_bound == dim1:
                    continue
                lines[back] = re.sub(
                    rf"(for\s*\(\s*int\s+{re.escape(loop_var)}\s*=\s*0\s*;\s*{re.escape(loop_var)}\s*<\s*)\d+(\s*;)",
                    rf"\g<1>{dim1}\2",
                    lines[back],
                )
                return "\n".join(lines)
            if loop_var == idx2:
                if current_bound == dim2:
                    continue
                lines[back] = re.sub(
                    rf"(for\s*\(\s*int\s+{re.escape(loop_var)}\s*=\s*0\s*;\s*{re.escape(loop_var)}\s*<\s*)\d+(\s*;)",
                    rf"\g<1>{dim2}\2",
                    lines[back],
                )
                return "\n".join(lines)

        return source
