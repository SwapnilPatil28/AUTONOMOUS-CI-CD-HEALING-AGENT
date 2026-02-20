"""Java bug detection analyzer - detects 6 bug types in Java code."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class JavaAnalyzerService:
    """Analyze Java files for SYNTAX, LINTING, LOGIC, TYPE_ERROR, IMPORT, INDENTATION errors."""

    def analyze(self, repo_path: Path) -> list[dict[str, Any]]:
        """Analyze all Java files in the repository."""
        failures: list[dict[str, Any]] = []
        for file_path in self._iter_java_files(repo_path):
            relative_path = file_path.relative_to(repo_path).as_posix()
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            
            failures.extend(self._find_syntax_errors(source, relative_path))
            failures.extend(self._find_linting_errors(source, relative_path))
            failures.extend(self._find_import_errors(source, relative_path))
            failures.extend(self._find_logic_errors(source, relative_path))
            failures.extend(self._find_type_errors(source, relative_path))
            failures.extend(self._find_indentation_errors(source, relative_path))
        
        return failures

    def _iter_java_files(self, repo_path: Path):
        """Iterate through Java files, skipping ignored directories."""
        ignored_dirs = {".git", "target", "node_modules", ".gradle", "build", "__pycache__"}
        for file_path in repo_path.rglob("*.java"):
            if any(part in ignored_dirs for part in file_path.parts):
                continue
            yield file_path

    def _find_syntax_errors(self, source: str, file_path: str) -> list[dict[str, Any]]:
        """Detect SYNTAX errors: missing semicolons, braces, parentheses."""
        failures = []
        lines = source.split("\n")
        
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            
            # Missing semicolon at end of statement
            if (
                stripped
                and not stripped.endswith((";", "{", "}", ",", ")", "//", "/*", "*/"))
                and not re.match(r"^\s*(for|if|while|else|class|interface|try|catch|finally|switch|public|private|protected|static)\b", stripped)
                and ("=" in stripped or stripped.endswith(")") or re.search(r"\breturn\b", stripped))
            ):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "SYNTAX",
                    "message": "Missing semicolon at end of statement",
                })
            
            # Missing opening brace for method/class
            if re.search(r"(public|private|protected)?\s*(static)?\s*(class|interface|void|int|String|boolean|double|float)\s+\w+\s*\([^)]*\)\s*$", stripped):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "SYNTAX",
                    "message": "Missing opening brace after method/class declaration",
                })

            # Missing closing parenthesis
            if stripped.count("(") > stripped.count(")") and stripped.endswith(";"):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "SYNTAX",
                    "message": "Missing closing parenthesis",
                })

            # Missing closing bracket
            if stripped.count("[") > stripped.count("]") and stripped.endswith(";"):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "SYNTAX",
                    "message": "Missing closing bracket",
                })
        
        return failures

    def _find_linting_errors(self, source: str, file_path: str) -> list[dict[str, Any]]:
        """Detect LINTING errors: unused imports, naming conventions."""
        failures = []
        lines = source.split("\n")
        
        # Find unused imports
        import_lines = []
        for idx, line in enumerate(lines, 1):
            if re.match(r"^\s*import\s+", line):
                import_lines.append((idx, line))
        
        for idx, import_line in import_lines:
            match = re.search(r"import\s+([\w.]+);", import_line)
            if match:
                imported = match.group(1).split(".")[-1]
                # Check if imported class is used in source
                if not re.search(r"\b" + re.escape(imported) + r"\b", source.replace(import_line, "")):
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LINTING",
                        "message": f"Unused import: {imported}",
                    })
        
        # Variable naming: should use camelCase
        for idx, line in enumerate(lines, 1):
            # Find variable declarations
            matches = re.findall(r"\b(int|String|double|boolean|float|long)\s+([a-zA-Z_]\w*)", line)
            for _, var_name in matches:
                if "_" in var_name and var_name != "_":  # snake_case detected
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LINTING",
                        "message": f"Variable '{var_name}' should use camelCase, not snake_case",
                    })

        # Parameter naming: should use camelCase
        for idx, line in enumerate(lines, 1):
            signature_match = re.search(r"\b\w[\w<>\[\]]*\s+\w+\s*\(([^)]*)\)", line)
            if not signature_match:
                continue
            params = [p.strip() for p in signature_match.group(1).split(",") if p.strip()]
            for param in params:
                parts = [part for part in param.split() if part]
                if not parts:
                    continue
                param_name = parts[-1]
                if "_" in param_name and param_name != "_":
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LINTING",
                        "message": f"parameter name should be camelCase: '{param_name}'",
                    })
        
        # Class naming: should use PascalCase
        for idx, line in enumerate(lines, 1):
            match = re.search(r"\bclass\s+([a-z]\w*)", line)
            if match:
                class_name = match.group(1)
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "LINTING",
                    "message": f"Class '{class_name}' should use PascalCase",
                })

        # Method naming: should use camelCase
        for idx, line in enumerate(lines, 1):
            match = re.search(r"\b(?:public|private|protected)?\s*(?:static\s+)?\w[\w<>\[\]]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
            if match:
                method_name = match.group(1)
                if "_" in method_name or method_name[:1].isupper():
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LINTING",
                        "message": f"method name should be camelCase: '{method_name}'",
                    })


        # Unused variables (simple heuristic)
        declared: dict[str, int] = {}
        for idx, line in enumerate(lines, 1):
            match = re.search(r"\b(?:int|String|double|boolean|float|long|char|byte|short|var)\s+([a-zA-Z_]\w*)\s*(?:=|;)", line)
            if match:
                name = match.group(1)
                if not name.startswith("_"):
                    declared[name] = idx

        for name, decl_line in declared.items():
            occurrences = len(re.findall(rf"\b{re.escape(name)}\b", source))
            if occurrences <= 1:
                failures.append({
                    "file": file_path,
                    "line_number": decl_line,
                    "bug_type": "LINTING",
                    "message": f"unused variable '{name}'",
                })
        
        return failures

    def _find_import_errors(self, source: str, file_path: str) -> list[dict[str, Any]]:
        """Detect IMPORT errors: wrong imports, imports after code."""
        failures = []
        lines = source.split("\n")
        
        first_code_line = None
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith("//") and not stripped.startswith("/*"):
                if not stripped.startswith(("package", "import", "*")):
                    first_code_line = idx
                    break
        
        # Check for imports after code
        for idx, line in enumerate(lines, 1):
            if idx > first_code_line and re.match(r"^\s*import\s+", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "IMPORT",
                    "message": "Import statement found after code",
                })

        # Incomplete import statements
        for idx, line in enumerate(lines, 1):
            if re.match(r"^\s*import\s*;\s*$", line) or re.match(r"^\s*import\s*$", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "IMPORT",
                    "message": "incomplete import statement",
                })
        
        return failures

    def _find_logic_errors(self, source: str, file_path: str) -> list[dict[str, Any]]:
        """Detect LOGIC errors: wrong operators, reversed comparisons, premature returns."""
        failures = []
        lines = source.split("\n")
        assigned_constants: list[tuple[int, str, float]] = []
        
        for idx, line in enumerate(lines, 1):
            # Wrong operator: += vs -=
            if re.search(r"(\w+)\s*\+=\s*(-?\d+)", line):
                # Could be wrong operator for decrement
                if "remove" in line.lower() or "decrement" in line.lower():
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "Possible wrong operator: using += for removal operation",
                    })
            
            if re.search(r"(\w+)\s*-=\s*(-?\d+)", line):
                # Could be wrong operator for increment
                if "add" in line.lower() or "increment" in line.lower() or "deposit" in line.lower():
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "Possible wrong operator: using -= for addition operation",
                    })

            # Accumulator subtraction likely wrong (total/sum)
            subtract_match = re.search(r"\b(total|sum|count)\w*\s*-=\s*\w+", line)
            if subtract_match and "remove" not in line.lower() and "decrement" not in line.lower():
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "LOGIC",
                    "message": "addition operation uses '-='",
                })
            
            # Wrong divisor for average
            if re.search(r"sum\s*\/\s*(\d+)", line) and "/" in line:
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "LOGIC",
                    "message": "Possible wrong divisor: dividing by constant instead of array length",
                })

            # Bitwise XOR used for exponentiation
            if re.search(r"\b\w+\s*\^\s*\w+\b", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "LOGIC",
                    "message": "bitwise XOR (^) detected, did you mean exponentiation?",
                })

            # String literal used instead of variable
            if "return" in line and "+" in line and re.search(r'\+\s*["\"][a-zA-Z_]\w*["\"]', line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "LOGIC",
                    "message": "string literal detected in expression, did you mean a variable?",
                })

            # Reversed comparison for max/min tracking
            compare = re.search(r"if\s*\(\s*([a-zA-Z_]\w*)\s*([<>])\s*([a-zA-Z_]\w*)\s*\)", line)
            if compare:
                left_name, operator, right_name = compare.group(1), compare.group(2), compare.group(3)
                if "max" in right_name.lower() and operator == "<" and "max" not in left_name.lower():
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "comparison for max uses '<', did you mean '>'?",
                    })
                if "min" in right_name.lower() and operator == ">" and "min" not in left_name.lower():
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "comparison for min uses '>', did you mean '<'?",
                    })

            # Return inside accumulation loop (heuristic)
            if re.search(r"\breturn\b", line):
                for back_idx in range(max(0, idx - 5), idx):
                    prev = lines[back_idx].strip()
                    if re.search(r"\bfor\b|\bwhile\b", prev) and any(tok in prev for tok in ["sum", "total", "count"]):
                        failures.append({
                            "file": file_path,
                            "line_number": idx,
                            "bug_type": "LOGIC",
                            "message": "return inside accumulation loop causes premature exit",
                        })
                        break

            const_assign = re.search(r"\b([a-zA-Z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?)\s*;", line)
            if const_assign:
                assigned_constants.append((idx, const_assign.group(1), float(const_assign.group(2))))
            
            # Reversed comparison
            if re.search(r"(if|while)\s*\([^)]*[!=]=[^)]*\)", line):
                if "not" in line or "!" in line:
                    # Could be reversed
                    pass

        # Min/max tracker initialized to constant
        for line_no, name, _value in assigned_constants:
            lower_name = name.lower()
            if "min" not in lower_name and "max" not in lower_name:
                continue
            for line in lines:
                compare = re.search(rf"if\s*\([^\)]*\b{name}\b\s*([<>])", line)
                if compare:
                    failures.append({
                        "file": file_path,
                        "line_number": line_no,
                        "bug_type": "LOGIC",
                        "message": "min/max tracker initialized to constant; use first iterable element instead",
                    })
                    break

        # Threshold tracker initialized too high/low
        high_hints = {"high", "highest", "top", "best", "max", "greatest"}
        low_hints = {"low", "lowest", "bottom", "worst", "min", "smallest"}
        for line_no, name, value in assigned_constants:
            lower_name = name.lower()
            if any(hint in lower_name for hint in high_hints):
                for line in lines:
                    if re.search(rf"if\s*\([^\)]*>\s*\b{name}\b", line) and value > 0:
                        failures.append({
                            "file": file_path,
                            "line_number": line_no,
                            "bug_type": "LOGIC",
                            "message": "threshold tracker initialized too high for '>' selection",
                        })
                        break
            if any(hint in lower_name for hint in low_hints):
                for line in lines:
                    if re.search(rf"if\s*\([^\)]*<\s*\b{name}\b", line) and value < 0:
                        failures.append({
                            "file": file_path,
                            "line_number": line_no,
                            "bug_type": "LOGIC",
                            "message": "threshold tracker initialized too low for '<' selection",
                        })
                        break
        
        return failures

    def _find_type_errors(self, source: str, file_path: str) -> list[dict[str, Any]]:
        """Detect TYPE_ERROR: int+String, type mismatches."""
        failures = []
        lines = source.split("\n")
        
        for idx, line in enumerate(lines, 1):
            # String concatenation with numbers without toString
            if re.search(r'".*"\s*\+\s*(\w+(?:\.\w+)?)\s*[,;)]', line):
                if not re.search(r'(toString\(\)|String\.valueOf\()', line):
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "TYPE_ERROR",
                        "message": "type mismatch: string concatenation requires conversion",
                    })
            
            # Number + String
            if re.search(r"\d\s*\+\s*\"", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "TYPE_ERROR",
                    "message": "Type error: adding number to String",
                })

            # String literal assigned to numeric type
            if re.search(r"\b(int|long|double|float)\s+\w+\s*=\s*\"-?\d+(?:\.\d+)?\"\s*;", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "TYPE_ERROR",
                    "message": "assigned string literal to numeric type",
                })

            # Mixed numeric/string collection literal
            if re.search(r"\{[^}]*\d+[^}]*['\"]\d+['\"][^}]*\}", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "TYPE_ERROR",
                    "message": "mixed numeric and string values in collection",
                })
        
        return failures

    def _find_indentation_errors(self, source: str, file_path: str) -> list[dict[str, Any]]:
        """Detect INDENTATION errors: improper indentation after braces."""
        failures = []
        lines = source.split("\n")
        
        for idx in range(len(lines) - 1):
            line = lines[idx]
            next_line = lines[idx + 1]
            
            # After opening brace, next non-empty line should be indented more
            if line.rstrip().endswith("{"):
                if next_line.strip() and not next_line.strip().startswith("}"):
                    current_indent = len(line) - len(line.lstrip())
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= current_indent:
                        failures.append({
                            "file": file_path,
                            "line_number": idx + 2,
                            "bug_type": "INDENTATION",
                            "message": "Missing indentation after opening brace",
                        })
        
        return failures
