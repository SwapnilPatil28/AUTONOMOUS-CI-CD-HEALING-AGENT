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
        class_names = re.findall(r"\bclass\s+([A-Za-z_]\w*)", source)
        
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            # Import statements must end with semicolon
            if re.match(r"^\s*import\s+[\w.]+\s*$", stripped):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "SYNTAX",
                    "message": "Missing semicolon at end of statement",
                })
            
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

            # Method call statement missing semicolon (e.g., System.out.println(...))
            if (
                stripped.endswith(")")
                and not stripped.endswith(");")
                and not re.match(r"^\s*(if|for|while|switch|catch|synchronized)\b", stripped)
                and not re.search(r"\)\s*\{\s*$", stripped)
                and "class" not in stripped
                and "interface" not in stripped
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

            # Constructor name must match class name exactly
            ctor_match = re.match(r"^\s*(public|private|protected)\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{?\s*$", stripped)
            if ctor_match and class_names:
                ctor_name = ctor_match.group(2)
                if ctor_name not in class_names and not re.match(r"^(if|for|while|switch|catch)$", ctor_name):
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "SYNTAX",
                        "message": "Constructor name does not match class name",
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
        class_names = set(re.findall(r"\bclass\s+([A-Za-z_]\w*)", source))
        
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

            # Scanner class case sensitivity
            if re.search(r"import\s+java\.util\.scanner\s*;?", import_line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "LINTING",
                    "message": "Scanner type should be capitalized",
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
            match = re.match(
                r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
                r"([A-Za-z_][\w<>\[\]]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*(?:\{|throws\b)",
                line,
            )
            if match:
                return_type = match.group(1)
                method_name = match.group(2)
                if return_type in {"if", "for", "while", "switch", "catch", "new"}:
                    continue
                if method_name in class_names:
                    continue
                if "_" in method_name:
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

        # Raw types (no generics) - HashMap, ArrayList, Map, List without <>
        for idx, line in enumerate(lines, 1):
            # HashMap/ArrayList/Map/List without generics
            raw_type_match = re.search(r'\b(HashMap|ArrayList|Map|List|Set|HashSet)\s+(\w+)\s*=\s*new\s+\1\s*\(', line)
            if raw_type_match and '<' not in line:
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "LINTING",
                    "message": f"Raw type usage: {raw_type_match.group(1)} should use generics",
                })

        # Unused empty methods
        for idx, line in enumerate(lines, 1):
            method_match = re.match(
                r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?"
                r"(?:void|int|String|boolean|double|float|long|char|byte|short)\s+"
                r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{?\s*$",
                line,
            )
            if method_match:
                method_name = method_match.group(1)
                method_end = self._find_method_end(lines, idx - 1)
                method_body = "\n".join(lines[idx:method_end])
                
                # Check if method body is empty (only whitespace, comments, or single closing brace)
                body_stripped = re.sub(r'//.*|/\*.*?\*/', '', method_body, flags=re.DOTALL).strip()
                if body_stripped in ('', '}', '{}'):
                    # Check if method is used anywhere
                    method_calls = len(re.findall(rf'\b{method_name}\s*\(', source))
                    if method_calls <= 1:  # Only the definition itself
                        failures.append({
                            "file": file_path,
                            "line_number": idx,
                            "bug_type": "LINTING",
                            "message": f"Unused empty method: {method_name}",
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
        seen_logic: set[tuple[int, str]] = set()

        # Track Java 2D array declarations: name -> (dim1, dim2)
        array_dims: dict[str, tuple[int, int]] = {}
        for idx, line in enumerate(lines, 1):
            arr_decl = re.search(r"\b\w+\s*\[\]\s*\[\]\s*([A-Za-z_]\w*)\s*=\s*new\s+\w+\[(\d+)\]\[(\d+)\]", line)
            if arr_decl:
                array_dims[arr_decl.group(1)] = (int(arr_decl.group(2)), int(arr_decl.group(3)))
        
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

            # Detect possible 2D array loop bound overflow from constants
            access = re.search(r"\b([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*)\s*\]\s*\[\s*([A-Za-z_]\w*)\s*\]", line)
            if access:
                arr_name, idx1, idx2 = access.group(1), access.group(2), access.group(3)
                if arr_name in array_dims:
                    dim1, dim2 = array_dims[arr_name]
                    bound1 = self._find_loop_bound(lines, idx, idx1)
                    bound2 = self._find_loop_bound(lines, idx, idx2)
                    if bound1 is not None and bound1 > dim1 and (idx, "overflow1") not in seen_logic:
                        failures.append({
                            "file": file_path,
                            "line_number": idx,
                            "bug_type": "LOGIC",
                            "message": "Loop bound exceeds array dimension",
                        })
                        seen_logic.add((idx, "overflow1"))
                    if bound2 is not None and bound2 > dim2 and (idx, "overflow2") not in seen_logic:
                        failures.append({
                            "file": file_path,
                            "line_number": idx,
                            "bug_type": "LOGIC",
                            "message": "Loop bound exceeds array dimension",
                        })
                        seen_logic.add((idx, "overflow2"))

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

        # isBoardFull-style reversed semantics: returns true on empty slot and false otherwise
        for idx, line in enumerate(lines, 1):
            if re.search(r"\bboolean\s+isBoardFull\s*\(", line):
                block_end = self._find_method_end(lines, idx - 1)
                block = "\n".join(lines[idx - 1:block_end])
                if re.search(r"if\s*\([^)]*==\s*'\-'[^)]*\)\s*\{?\s*return\s+true\s*;", block, re.DOTALL) and re.search(r"return\s+false\s*;", block):
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "isBoardFull returns true when empty slot found",
                    })

        # checkWin method exists but only row checks (no columns/diagonals)
        for idx, line in enumerate(lines, 1):
            if re.search(r"\bboolean\s+checkWin\s*\(", line):
                block_end = self._find_method_end(lines, idx - 1)
                block = "\n".join(lines[idx - 1:block_end])
                row_check = re.search(r"\[i\]\[0\].*\[i\]\[1\].*\[i\]\[2\]", block.replace(" ", ""))
                col_check = re.search(r"\[0\]\[i\].*\[1\]\[i\].*\[2\]\[i\]", block.replace(" ", ""))
                diag_check = re.search(r"\[0\]\[0\].*\[1\]\[1\].*\[2\]\[2\]|\[0\]\[2\].*\[1\]\[1\].*\[2\]\[0\]", block.replace(" ", ""))
                if row_check and not (col_check and diag_check):
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "checkWin missing column and/or diagonal checks",
                    })

        # Infinite loop risk when board-full method exists but not used in game loop
        has_board_full = bool(re.search(r"\bisBoardFull\s*\(", source))
        board_full_calls = len(re.findall(r"\bisBoardFull\s*\(", source))
        if has_board_full and board_full_calls <= 1:
            for idx, line in enumerate(lines, 1):
                if re.search(r"\bwhile\s*\(\s*true\s*\)", line):
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "missing tie-check in loop when board is full",
                    })
                    break

        # Infinite recursion detection: binary search with mid not incremented
        for idx, line in enumerate(lines, 1):
            # Look for recursive method calls with parameters
            recursive_call = re.search(r'(\w+)\s*\(([^)]+)\)', line)
            if recursive_call:
                method_name = recursive_call.group(1)
                params = recursive_call.group(2)
                param_list = [p.strip() for p in params.split(',')]
                
                # Check if this is inside a method with same name (recursion)
                for back_idx in range(max(0, idx - 15), idx):
                    method_sig = re.search(rf'\b{method_name}\s*\(([^)]+)\)', lines[back_idx])
                    if method_sig:
                        # Extract parameter names from method signature
                        sig_params = method_sig.group(1)
                        sig_param_names = []
                        for param in sig_params.split(','):
                            parts = param.strip().split()
                            if len(parts) >= 2:
                                sig_param_names.append(parts[-1])  # Last part is variable name
                        
                        # For binary search pattern (4 params: array, target, low, high)
                        if len(sig_param_names) >= 4 and len(param_list) >= 4:
                            # Get the middle parameter name (typically 'mid', 'middle', 'center', etc.)
                            # Find it in the method body
                            for body_idx in range(back_idx, idx):
                                mid_calc = re.search(r'\b(\w+)\s*=\s*\([^)]*\+[^)]*\)\s*/\s*2', lines[body_idx])
                                if mid_calc:
                                    mid_var = mid_calc.group(1)
                                    # Check if this mid variable is used as boundary without +/-1
                                    if mid_var in param_list:
                                        # Check if used without adjustment
                                        mid_positions = [i for i, p in enumerate(param_list) if p == mid_var]
                                        for pos in mid_positions:
                                            # mid should not be directly used as low or high boundary
                                            if pos in [2, 3] and not re.search(rf'{mid_var}\s*[+-]\s*1', params):
                                                failures.append({
                                                    "file": file_path,
                                                    "line_number": idx,
                                                    "bug_type": "LOGIC",
                                                    "message": "Infinite recursion: mid used as boundary without increment/decrement",
                                                })
                                    break
                        break

        # Inverted rotated array search logic detection
        for idx, line in enumerate(lines, 1):
            # Look for rotated array binary search pattern - generic array and variable names
            # Pattern: if (arr[left] <= arr[mid])
            array_compare = re.search(r'if\s*\([^)]*(\w+)\s*\[\s*(\w+)\s*\]\s*<=\s*\1\s*\[\s*(\w+)\s*\]', line)
            if array_compare:
                array_name = array_compare.group(1)
                left_var = array_compare.group(2)
                mid_var = array_compare.group(3)
                
                # Look for the condition and assignments in the if block
                method_start = max(0, idx - 1)
                method_end = min(len(lines), idx + 15)
                context_lines = lines[method_start:method_end]
                context = "\n".join(context_lines)
                
                # Look for pattern: if (arr[left] <= target && target < arr[mid]) inside the outer if
                # This means "target is in sorted left half"
                # Correct: should reduce right boundary (high = mid - 1)
                # Inverted: increases left boundary (low = mid + 1) instead
                inner_if = re.search(
                    rf'if\s*\([^)]*{array_name}\s*\[\s*{left_var}\s*\]\s*<=\s*(\w+)\s*&&\s*\1\s*<\s*{array_name}\s*\[\s*{mid_var}\s*\][^{{]*\{{[^}}]*{left_var}\s*=',
                    context
                )
                if inner_if:
                    # Found: target in sorted left, but code increases left (searches right) - INVERTED
                    failures.append({
                        "file": file_path,
                        "line_number": idx,
                        "bug_type": "LOGIC",
                        "message": "Inverted rotated array search logic",
                    })
        
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

            # char assigned from String literal
            if re.search(r"\bchar\s+\w+\s*=\s*\"[^\"]+\"\s*;", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "TYPE_ERROR",
                    "message": "char assigned from String literal",
                })

            # int assigned from scanner.next() instead of nextInt()
            if re.search(r"\bint\s+\w+\s*=\s*\w+\.next\s*\(\s*\)\s*;", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "TYPE_ERROR",
                    "message": "int assigned from scanner.next()",
                })

            # Scanner type should be capitalized in declarations/usages
            if re.search(r"\bscanner\s+\w+\s*=\s*new\s+scanner\s*\(", line):
                failures.append({
                    "file": file_path,
                    "line_number": idx,
                    "bug_type": "TYPE_ERROR",
                    "message": "Scanner type should be capitalized",
                })

        # Return type mismatch detection - find method signatures and track their return types
        method_signatures = []
        for idx, line in enumerate(lines, 1):
            sig_match = re.match(
                r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?"
                r"(int|String|double|float|long|boolean|void|char|byte|short)\s+"
                r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:\{|throws\b)",
                line,
            )
            if sig_match:
                return_type = sig_match.group(1)
                method_name = sig_match.group(2)
                method_signatures.append((idx, return_type, method_name))

        # Check return statements within method bodies for type mismatches
        for method_line, expected_type, method_name in method_signatures:
            method_end = self._find_method_end(lines, method_line - 1)
            method_body = "\n".join(lines[method_line - 1:method_end])
            
            # Find return statements within this method
            for body_idx, body_line in enumerate(lines[method_line:method_end], method_line + 1):
                # int method returning String literal
                if expected_type == "int" and re.search(r'\breturn\s+"[^"]*"\s*;', body_line):
                    failures.append({
                        "file": file_path,
                        "line_number": body_idx,
                        "bug_type": "TYPE_ERROR",
                        "message": f"int method returning String literal",
                    })
                
                # int method returning decimal literal
                if expected_type == "int" and re.search(r'\breturn\s+-?\d+\.\d+\s*;', body_line):
                    failures.append({
                        "file": file_path,
                        "line_number": body_idx,
                        "bug_type": "TYPE_ERROR",
                        "message": f"int method returning decimal literal",
                    })
                
                # String method returning int literal (no quotes)
                if expected_type == "String" and re.search(r'\breturn\s+-?\d+\s*;', body_line) and not re.search(r'"', body_line):
                    failures.append({
                        "file": file_path,
                        "line_number": body_idx,
                        "bug_type": "TYPE_ERROR",
                        "message": f"String method returning int literal",
                    })

        # Generic type constraint violation (Map<String, Double> receiving String value)
        for idx, line in enumerate(lines, 1):
            # Map<String, Double> declaration
            map_decl = re.search(r'Map<[^,]+,\s*Double>\s+(\w+)\s*=\s*new\s+HashMap', line)
            if map_decl:
                map_name = map_decl.group(1)
                # Look for String literal being put into this map (should be numeric)
                for scan_idx in range(idx, min(idx + 20, len(lines) + 1)):
                    put_line = lines[scan_idx - 1]
                    if re.search(rf'\b{map_name}\.put\s*\([^,]+,\s*"[^"]+"\s*\)', put_line):
                        failures.append({
                            "file": file_path,
                            "line_number": scan_idx,
                            "bug_type": "TYPE_ERROR",
                            "message": "Map<String, Double> receiving String value instead of Double",
                        })
        
        return failures

    @staticmethod
    def _find_loop_bound(lines: list[str], current_line: int, variable: str) -> int | None:
        start = max(0, current_line - 8)
        for back_idx in range(current_line - 1, start - 1, -1):
            loop_match = re.search(
                rf"for\s*\(\s*int\s+{re.escape(variable)}\s*=\s*0\s*;\s*{re.escape(variable)}\s*<\s*(\d+)\s*;",
                lines[back_idx],
            )
            if loop_match:
                return int(loop_match.group(1))
        return None

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
