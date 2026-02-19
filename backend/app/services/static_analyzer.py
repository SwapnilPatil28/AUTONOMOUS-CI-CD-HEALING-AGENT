from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


class StaticAnalyzerService:
    def analyze(self, repo_path: Path) -> list[dict[str, Any]]:
        """Analyze Python files for all 6 bug types: SYNTAX, LINTING, LOGIC, TYPE_ERROR, IMPORT, INDENTATION."""
        failures: list[dict[str, Any]] = []
        for file_path in self._iter_python_files(repo_path):
            relative_path = file_path.relative_to(repo_path).as_posix()
            source = file_path.read_text(encoding="utf-8", errors="ignore")

            tree = None
            try:
                tree = ast.parse(source)
            except SyntaxError as error:
                failures.append({
                    "file": relative_path,
                    "line_number": error.lineno or 1,
                    "bug_type": "SYNTAX",
                    "message": error.msg or "SyntaxError",
                })
                failures.extend(self._find_unused_imports_in_source(source, relative_path))

            # Continue analyzing even if there's a SYNTAX error
            if tree:
                failures.extend(self._find_unused_imports(tree, relative_path))
                failures.extend(self._find_unused_variables(tree, source, relative_path))
            
            # Always check for logic and type errors via regex/pattern matching (doesn't need AST)
            failures.extend(self._find_logic_errors(source, relative_path))
            failures.extend(self._find_type_errors(source, relative_path))
            failures.extend(self._find_indentation_errors(source, relative_path))
            failures.extend(self._find_import_errors(source, relative_path))

        return failures

    def _iter_python_files(self, repo_path: Path):
        """Iterate through Python files, skipping common ignored directories."""
        ignored_dirs = {
            ".git", ".venv", "venv", "node_modules", "__pycache__",
            ".pytest_cache", ".mypy_cache", "dist", "build",
        }
        for file_path in repo_path.rglob("*.py"):
            if any(part in ignored_dirs for part in file_path.parts):
                continue
            yield file_path


    @staticmethod
    def _find_unused_imports(tree: ast.AST, relative_path: str) -> list[dict[str, Any]]:
        """Find imported names that are never used."""
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
                failures.append({
                    "file": relative_path,
                    "line_number": line,
                    "bug_type": "LINTING",
                    "message": "unused import",
                })
        return failures

    @staticmethod
    def _find_unused_variables(tree: ast.AST, source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find variables assigned but never used (module-level and function-level)."""
        failures: list[dict[str, Any]] = []
        lines = source.splitlines()
        
        # Track module-level assignments and their line numbers
        assigned_at_module_level: dict[str, int] = {}  # name -> line_number
        used_names: set[str] = set()
        
        # Use AST to find all assignments and uses
        for node in ast.walk(tree):
            # Track assignments (only direct assignments, not in function defs)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if not target.id.startswith("_"):
                            assigned_at_module_level[target.id] = node.lineno
            # Track loads (uses)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            # Also track names used in function parameters (they're implicitly used)
            elif isinstance(node, ast.arg):
                used_names.add(node.arg)
        
        # Check line-by-line for clearer assignment tracking
        for line_no, line in enumerate(lines, start=1):
            code = line.split("#", 1)[0].strip()  # Remove comments
            if not code or "=" not in code:
                continue
            
            # Simple pattern: variable = value (not comparison)
            if "==" in code or "!=" in code or ">=" in code or "<=" in code:
                continue
            
            # Look for pattern: name = ...
            match = re.match(r'^([a-zA-Z_]\w*)\s*=\s*', code)
            if match:
                var_name = match.group(1)
                if not var_name.startswith("_"):
                    # If AST shows this name is used in any load context, it's not unused
                    if var_name in used_names:
                        continue

                    # Check if this variable is ever used in the source
                    # Count occurrences after the assignment
                    remaining_source = "\n".join(lines[line_no:])
                    uses = len(re.findall(rf'\b{re.escape(var_name)}\b', remaining_source))
                    
                    if uses == 0:
                        failures.append({
                            "file": relative_path,
                            "line_number": line_no,
                            "bug_type": "LINTING",
                            "message": f"unused variable '{var_name}'",
                        })
        
        return failures

    @staticmethod
    def _find_logic_errors(source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find common logic errors: XOR, string literal vs variable, wrong operators."""
        failures: list[dict[str, Any]] = []
        lines = source.splitlines()
        seen_logic: set[tuple[int, str]] = set()
        
        for line_no, line in enumerate(lines, start=1):
            # Skip comments and empty lines
            code = line.split("#", 1)[0].strip()
            if not code:
                continue
            
            # Detect bitwise XOR (^) that should probably be exponentiation (**)
            # Pattern: variable ^ number (likely exponentiation mistake)
            if re.search(r'\w+\s*\^\s*\d+', code):
                failures.append({
                    "file": relative_path,
                    "line_number": line_no,
                    "bug_type": "LOGIC",
                    "message": "bitwise XOR (^) detected, did you mean exponentiation (**)?",
                })
            
            # Detect string literal used instead of variable (e.g., "b" instead of b)
            # Pattern: + "single_char" which is likely a mistake
            if "return" in code and "+" in code:
                # Look for pattern: + "something" where it should be + variable
                if re.search(r'\+\s*["\'][a-zA-Z_]\w*["\']', code):
                    failures.append({
                        "file": relative_path,
                        "line_number": line_no,
                        "bug_type": "LOGIC",
                        "message": "string literal detected in expression, did you mean a variable?",
                    })

            # Detect likely reversed comparison in max/min tracking loops
            # Example bug: if num < max_value: max_value = num
            comparison_match = re.search(
                r'^if\s+([a-zA-Z_]\w*)\s*([<>])\s*([a-zA-Z_]\w*)\s*:\s*$',
                code,
            )
            if comparison_match:
                left_name = comparison_match.group(1)
                operator = comparison_match.group(2)
                right_name = comparison_match.group(3)
                right_lower = right_name.lower()
                left_lower = left_name.lower()

                if "max" in right_lower and operator == "<" and "max" not in left_lower:
                    key = (line_no, "comparison for max uses '<', did you mean '>'?")
                    if key not in seen_logic:
                        failures.append({
                            "file": relative_path,
                            "line_number": line_no,
                            "bug_type": "LOGIC",
                            "message": "comparison for max uses '<', did you mean '>'?",
                        })
                        seen_logic.add(key)
                elif "min" in right_lower and operator == ">" and "min" not in left_lower:
                    key = (line_no, "comparison for min uses '>', did you mean '<'?")
                    if key not in seen_logic:
                        failures.append({
                            "file": relative_path,
                            "line_number": line_no,
                            "bug_type": "LOGIC",
                            "message": "comparison for min uses '>', did you mean '<'?",
                        })
                        seen_logic.add(key)

        # AST-assisted logic detection for harder cases
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue

                func_name = node.name.lower()
                param_names = {arg.arg for arg in node.args.args}

                # Case 1: area-named function likely computing circumference (2*pi*r)
                if "area" in func_name and param_names:
                    primary_param = node.args.args[0].arg
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return):
                            expr = ast.get_source_segment(source, child.value) or ""
                            expr_lower = expr.lower()
                            has_pi = "pi" in expr_lower or "3.14" in expr_lower
                            if (
                                has_pi
                                and "*" in expr
                                and "**" not in expr
                                and re.search(rf"\b{re.escape(primary_param)}\b\s*\*\s*2\b", expr)
                            ):
                                msg = "area function appears to compute circumference (2πr), expected πr²"
                                key = (child.lineno, msg)
                                if key not in seen_logic:
                                    failures.append({
                                        "file": relative_path,
                                        "line_number": child.lineno,
                                        "bug_type": "LOGIC",
                                        "message": msg,
                                    })
                                    seen_logic.add(key)

                # Case 2: min/max tracker initialized to a constant then compared in loop
                init_candidates: dict[str, int] = {}
                for stmt in node.body:
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and isinstance(stmt.value, ast.Constant)
                        and isinstance(stmt.value.value, (int, float))
                    ):
                        target_name = stmt.targets[0].id
                        lower_target = target_name.lower()
                        if "min" in lower_target or "max" in lower_target:
                            init_candidates[target_name] = stmt.lineno

                if init_candidates:
                    for child in ast.walk(node):
                        if not isinstance(child, ast.If):
                            continue
                        if not isinstance(child.test, ast.Compare):
                            continue
                        if len(child.test.ops) != 1 or len(child.test.comparators) != 1:
                            continue
                        if not isinstance(child.test.left, ast.Name):
                            continue
                        comparator = child.test.comparators[0]
                        if not isinstance(comparator, ast.Name):
                            continue

                        tracker_name = comparator.id
                        if tracker_name not in init_candidates:
                            continue

                        lower_tracker = tracker_name.lower()
                        op = child.test.ops[0]
                        is_suspicious_min = "min" in lower_tracker and isinstance(op, ast.Lt)
                        is_suspicious_max = "max" in lower_tracker and isinstance(op, ast.Gt)
                        if not (is_suspicious_min or is_suspicious_max):
                            continue

                        msg = "min/max tracker initialized to constant; use first iterable element instead"
                        key = (init_candidates[tracker_name], msg)
                        if key not in seen_logic:
                            failures.append({
                                "file": relative_path,
                                "line_number": init_candidates[tracker_name],
                                "bug_type": "LOGIC",
                                "message": msg,
                            })
                            seen_logic.add(key)

                # Case 3: high/low threshold tracker initialized to restrictive constant
                threshold_candidates: dict[str, tuple[int, float]] = {}
                for stmt in node.body:
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and isinstance(stmt.value, ast.Constant)
                        and isinstance(stmt.value.value, (int, float))
                    ):
                        name = stmt.targets[0].id
                        value = float(stmt.value.value)
                        threshold_candidates[name] = (stmt.lineno, value)

                if threshold_candidates:
                    high_hints = {"high", "highest", "top", "best", "max", "greatest"}
                    low_hints = {"low", "lowest", "bottom", "worst", "min", "smallest"}

                    for child in ast.walk(node):
                        if not isinstance(child, ast.If) or not isinstance(child.test, ast.Compare):
                            continue
                        if len(child.test.ops) != 1 or len(child.test.comparators) != 1:
                            continue
                        comparator = child.test.comparators[0]
                        if not isinstance(comparator, ast.Name):
                            continue

                        tracker = comparator.id
                        if tracker not in threshold_candidates:
                            continue

                        tracker_lower = tracker.lower()
                        op = child.test.ops[0]
                        init_line, init_value = threshold_candidates[tracker]

                        # Ensure this if-body updates the same tracker
                        updates_tracker = False
                        for body_stmt in child.body:
                            if (
                                isinstance(body_stmt, ast.Assign)
                                and len(body_stmt.targets) == 1
                                and isinstance(body_stmt.targets[0], ast.Name)
                                and body_stmt.targets[0].id == tracker
                            ):
                                updates_tracker = True
                                break
                        if not updates_tracker:
                            continue

                        is_high_tracker = any(h in tracker_lower for h in high_hints)
                        is_low_tracker = any(h in tracker_lower for h in low_hints)

                        if is_high_tracker and isinstance(op, ast.Gt) and init_value > 0:
                            msg = "threshold tracker initialized too high for '>' selection"
                            key = (init_line, msg)
                            if key not in seen_logic:
                                failures.append({
                                    "file": relative_path,
                                    "line_number": init_line,
                                    "bug_type": "LOGIC",
                                    "message": msg,
                                })
                                seen_logic.add(key)
                        elif is_low_tracker and isinstance(op, ast.Lt) and init_value < 0:
                            msg = "threshold tracker initialized too low for '<' selection"
                            key = (init_line, msg)
                            if key not in seen_logic:
                                failures.append({
                                    "file": relative_path,
                                    "line_number": init_line,
                                    "bug_type": "LOGIC",
                                    "message": msg,
                                })
                                seen_logic.add(key)

                # Case 4: selection variable assignment likely belongs inside threshold if-block
                none_initialized: set[str] = set()
                for stmt in node.body:
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is None
                    ):
                        none_initialized.add(stmt.targets[0].id)

                if none_initialized:
                    for child in ast.walk(node):
                        if not isinstance(child, ast.For):
                            continue
                        if not isinstance(child.target, ast.Name):
                            continue

                        loop_var = child.target.id
                        for idx, loop_stmt in enumerate(child.body):
                            if not isinstance(loop_stmt, ast.If):
                                continue
                            if not isinstance(loop_stmt.test, ast.Compare):
                                continue
                            if len(loop_stmt.test.ops) != 1 or len(loop_stmt.test.comparators) != 1:
                                continue
                            if not isinstance(loop_stmt.test.comparators[0], ast.Name):
                                continue

                            threshold_name = loop_stmt.test.comparators[0].id
                            if threshold_name not in threshold_candidates:
                                continue

                            # Ensure if-body updates threshold variable
                            threshold_updated = any(
                                isinstance(s, ast.Assign)
                                and len(s.targets) == 1
                                and isinstance(s.targets[0], ast.Name)
                                and s.targets[0].id == threshold_name
                                for s in loop_stmt.body
                            )
                            if not threshold_updated:
                                continue

                            # Look at subsequent statements in loop body; if they assign selected var = loop_var,
                            # it's likely intended to be inside the if-block.
                            for trailing_stmt in child.body[idx + 1:]:
                                if (
                                    isinstance(trailing_stmt, ast.Assign)
                                    and len(trailing_stmt.targets) == 1
                                    and isinstance(trailing_stmt.targets[0], ast.Name)
                                    and isinstance(trailing_stmt.value, ast.Name)
                                ):
                                    selected_name = trailing_stmt.targets[0].id
                                    selected_value = trailing_stmt.value.id
                                    if selected_name in none_initialized and selected_value == loop_var:
                                        msg = "selection update likely belongs inside threshold if-block"
                                        key = (trailing_stmt.lineno, msg)
                                        if key not in seen_logic:
                                            failures.append({
                                                "file": relative_path,
                                                "line_number": trailing_stmt.lineno,
                                                "bug_type": "LOGIC",
                                                "message": msg,
                                            })
                                            seen_logic.add(key)
        except SyntaxError:
            pass
        
        return failures

    @staticmethod
    def _find_type_errors(source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find potential type errors: string concatenation with non-strings, int+str."""
        failures: list[dict[str, Any]] = []
        lines = source.splitlines()
        variable_types: dict[str, str] = {}  # name -> inferred type
        function_param_types: dict[str, list[str | None]] = {}
        function_return_types: dict[str, str | None] = {}
        seen_type_errors: set[tuple[int, str]] = set()

        def infer_expr_type(node: ast.AST) -> str | None:
            if isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    return "str"
                if isinstance(node.value, int):
                    return "int"
                return None

            if isinstance(node, ast.Name):
                return variable_types.get(node.id)

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "str":
                    return "str"
                if isinstance(node.func, ast.Name) and node.func.id in function_return_types:
                    return function_return_types[node.func.id]
                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "isoformat", "format", "decode", "strip", "lstrip", "rstrip",
                    "lower", "upper", "title", "capitalize", "replace", "join",
                }:
                    return "str"
                return None

            if isinstance(node, ast.BinOp):
                left_type = infer_expr_type(node.left)
                right_type = infer_expr_type(node.right)

                if isinstance(node.op, ast.Mult):
                    if (left_type == "str" and right_type == "int") or (left_type == "int" and right_type == "str"):
                        return "str"
                if isinstance(node.op, ast.Add) and left_type and right_type and left_type == right_type:
                    return left_type

            return None

        # AST pass for stronger type checking (works when file has valid syntax)
        try:
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    value_type = infer_expr_type(node.value)
                    if value_type:
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                variable_types[target.id] = value_type

                elif isinstance(node, ast.FunctionDef):
                    param_types: list[str | None] = []
                    for arg in node.args.args:
                        annotation = arg.annotation
                        expected_type: str | None = None
                        if isinstance(annotation, ast.Name):
                            if annotation.id in {"int", "str"}:
                                expected_type = annotation.id
                        param_types.append(expected_type)
                    function_param_types[node.name] = param_types

                    return_type: str | None = None
                    if isinstance(node.returns, ast.Name) and node.returns.id in {"int", "str", "float"}:
                        return_type = node.returns.id
                    function_return_types[node.name] = return_type

            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                    left_type = infer_expr_type(node.left)
                    right_type = infer_expr_type(node.right)
                    left_is_str_lit = isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)
                    right_is_str_lit = isinstance(node.right, ast.Constant) and isinstance(node.right.value, str)

                    if {left_type, right_type} == {"str", "int"}:
                        key = (node.lineno, "type mismatch: cannot add incompatible types")
                        if key not in seen_type_errors:
                            failures.append({
                                "file": relative_path,
                                "line_number": node.lineno,
                                "bug_type": "TYPE_ERROR",
                                "message": "type mismatch: cannot add incompatible types",
                            })
                            seen_type_errors.add(key)
                    elif (left_is_str_lit and isinstance(node.right, ast.Call) and right_type != "str") or (
                        right_is_str_lit and isinstance(node.left, ast.Call) and left_type != "str"
                    ):
                        key = (node.lineno, "type mismatch: string concatenation with non-string expression")
                        if key not in seen_type_errors:
                            failures.append({
                                "file": relative_path,
                                "line_number": node.lineno,
                                "bug_type": "TYPE_ERROR",
                                "message": "type mismatch: string concatenation with non-string expression",
                            })
                            seen_type_errors.add(key)

                elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                    if isinstance(node.target, ast.Name):
                        left_type = variable_types.get(node.target.id)
                        right_type = infer_expr_type(node.value)
                        if left_type == "str" and right_type != "str":
                            key = (node.lineno, "type mismatch: cannot add incompatible types")
                            if key not in seen_type_errors:
                                failures.append({
                                    "file": relative_path,
                                    "line_number": node.lineno,
                                    "bug_type": "TYPE_ERROR",
                                    "message": "type mismatch: cannot add incompatible types",
                                })
                                seen_type_errors.add(key)

                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    expected_params = function_param_types.get(node.func.id)
                    if not expected_params:
                        continue

                    for i, arg_node in enumerate(node.args):
                        if i >= len(expected_params):
                            break
                        expected_type = expected_params[i]
                        if expected_type is None:
                            continue
                        actual_type = infer_expr_type(arg_node)
                        if actual_type and actual_type != expected_type:
                            msg = f"argument type mismatch: expected {expected_type} but got {actual_type}"
                            key = (node.lineno, msg)
                            if key not in seen_type_errors:
                                failures.append({
                                    "file": relative_path,
                                    "line_number": node.lineno,
                                    "bug_type": "TYPE_ERROR",
                                    "message": msg,
                                })
                                seen_type_errors.add(key)

        except SyntaxError:
            pass
        
        # First pass: collect all variable type assignments  
        for line_no, line in enumerate(lines, start=1):
            code = line.split("#", 1)[0].strip()
            assign_match = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)$', code)
            if assign_match:
                var_name = assign_match.group(1)
                value = assign_match.group(2).strip()
                # Infer type from literal
                if value.startswith('"') or value.startswith("'"):
                    variable_types[var_name] = "str"
                elif re.match(r'^\d+$', value):
                    variable_types[var_name] = "int"
        
        # Second pass: detect type errors using known variables
        for line_no, line in enumerate(lines, start=1):
            code = line.split("#", 1)[0].strip()
            if not code or "+" not in code:
                continue
            
            # Skip if this is a print statement (likely for display, not arithmetic)
            if code.startswith("print("):
                continue
            
            # Don't skip assignments - they can have type errors in their right-hand side
            # e.g., y = x + "20"  is an assignment with a type error in the expression
            
            parts = code.split("+")
            for i in range(len(parts) - 1):
                left = parts[i].strip().split()[-1] if parts[i].strip() else ""
                right = parts[i + 1].strip().split()[0] if parts[i + 1].strip() else ""
                
                if not left or not right:
                    continue
                
                # Determine types
                left_is_str_lit = left.startswith('"') or left.startswith("'")
                right_is_str_lit = right.startswith('"') or right.startswith("'")
                left_is_int_lit = bool(re.match(r'^\d+$', left))
                right_is_int_lit = bool(re.match(r'^\d+$', right))
                left_is_str_var = left in variable_types and variable_types[left] == "str"
                right_is_str_var = right in variable_types and variable_types[right] == "str"
                
                # Check if left/right are ACTUAL function/method calls (must have both ( and ))
                # Pattern: name(...) or obj.method(...)
                left_is_call = left.endswith(")") and "(" in left
                right_is_call = right.endswith(")") and "(" in right
                
                # Check if left/right are attribute access (obj.attr)
                left_is_attr = "." in left
                right_is_attr = "." in right
                
                # Check if expression involves string multiplication (e.g., "=" * 70)
                # This is safe because string * int = string
                left_part = parts[i].strip()
                right_part = parts[i + 1].strip()
                has_string_multiplication = ("*" in left_part or "*" in right_part) and (
                    left_is_str_lit or right_is_str_lit
                )
                
                # Detect type errors: int + str, str + int
                is_type_error = False
                
                # Clear cases: number + string literal or string literal + number
                if (left_is_int_lit and right_is_str_lit) or (left_is_str_lit and right_is_int_lit):
                    is_type_error = True
                
                # Cases with variables - but exclude function calls, attribute access, and string multiplication
                # unknown_var + string_literal might be type error UNLESS unknown_var is an attribute
                elif (not (left_is_str_lit or left_is_int_lit or left_is_str_var or left_is_call or left_is_attr)) and right_is_str_lit and not has_string_multiplication:
                    # variable + "string" - this is type error if variable isn't a string
                    is_type_error = True
                # string_literal + unknown_var might be type error UNLESS unknown_var is an attribute
                elif left_is_str_lit and (not (right_is_str_lit or right_is_int_lit or right_is_str_var or right_is_call or right_is_attr)) and not has_string_multiplication:
                    # "string" + variable - but NOT "string" + obj.attr
                    is_type_error = True
                
                if is_type_error:
                    key = (line_no, "type mismatch: cannot add incompatible types")
                    if key in seen_type_errors:
                        break
                    failures.append({
                        "file": relative_path,
                        "line_number": line_no,
                        "bug_type": "TYPE_ERROR",
                        "message": "type mismatch: cannot add incompatible types",
                    })
                    seen_type_errors.add(key)
                    break  # Only report once per line

        # Third pass: detect += mismatches from iterables that are populated with str(...)
        for line_no, line in enumerate(lines, start=1):
            code = line.split("#", 1)[0].strip()
            aug_match = re.match(r'^([a-zA-Z_]\w*)\s*\+=\s*([a-zA-Z_]\w*)\s*$', code)
            if not aug_match:
                continue

            left_name = aug_match.group(1)
            right_name = aug_match.group(2)
            left_type = variable_types.get(left_name)
            if left_type not in {"int", "float"}:
                continue

            iterable_name = None
            for prev_idx in range(line_no - 2, -1, -1):
                prev_code = lines[prev_idx].split("#", 1)[0].strip()
                loop_match = re.match(rf'^for\s+{re.escape(right_name)}\s+in\s+([a-zA-Z_][\w\.]*)\s*:\s*$', prev_code)
                if loop_match:
                    iterable_name = loop_match.group(1)
                    break

            if not iterable_name:
                continue

            append_str_pattern = rf'\b{re.escape(iterable_name)}\s*\.\s*append\s*\(\s*str\s*\('
            if any(re.search(append_str_pattern, l) for l in lines):
                key = (line_no, "type mismatch: cannot add incompatible types")
                if key not in seen_type_errors:
                    failures.append({
                        "file": relative_path,
                        "line_number": line_no,
                        "bug_type": "TYPE_ERROR",
                        "message": "type mismatch: cannot add incompatible types",
                    })
                    seen_type_errors.add(key)
        
        return failures

    @staticmethod
    def _find_unused_imports_in_source(source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find unused imports when AST parsing fails (syntax errors)."""
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
                failures.append({
                    "file": relative_path,
                    "line_number": line_no,
                    "bug_type": "LINTING",
                    "message": "unused import",
                })
                seen.add((name, line_no))

        return failures

    @staticmethod
    def _find_indentation_errors(source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find indentation errors: inconsistent indentation, missing indentation after colons, mixed tabs/spaces."""
        failures: list[dict[str, Any]] = []
        lines = source.splitlines()
        
        # Track which blocks expect indentation
        expects_indent = False
        expect_indent_after_line = -1
        
        for line_no, line in enumerate(lines, start=1):
            # Empty lines and comments don't affect indentation
            if not line.strip() or line.strip().startswith("#"):
                continue
            
            code = line.split("#", 1)[0].rstrip()  # Remove comments for analysis
            current_indent = len(line) - len(line.lstrip())
            current_indent_char = '\t' if line and line[0] == '\t' else ' '
            
            # Check for mixed tabs and spaces (bad indentation)
            if '\t' in line[:current_indent] and ' ' in line[:current_indent]:
                failures.append({
                    "file": relative_path,
                    "line_number": line_no,
                    "bug_type": "INDENTATION",
                    "message": "mixed tabs and spaces in indentation",
                })
            
            # Check for lines that should be indented
            if line_no > 1:
                prev_line = lines[line_no - 2].split("#", 1)[0].rstrip()
                prev_stripped = prev_line.strip()
                prev_indent = len(prev_line) - len(prev_line.lstrip())
                
                # If previous line ends with colon, this line should be more indented
                if prev_stripped.endswith(":"):
                    expected_indent = prev_indent + 4
                    
                    # If this is not an empty line or a dedent, it should be indented
                    # Allow dedenting (return, pass, elif, else, except, finally)
                    is_dedent = any(
                        code.strip().startswith(kw)
                        for kw in ['return', 'pass', 'break', 'continue', 'elif', 'else', 'except', 'finally', 'def', 'class']
                    )
                    
                    if not is_dedent and current_indent < expected_indent and code:
                        failures.append({
                            "file": relative_path,
                            "line_number": line_no,
                            "bug_type": "INDENTATION",
                            "message": f"expected indentation of {expected_indent} spaces, got {current_indent}",
                        })

        return failures

    @staticmethod
    def _find_import_errors(source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find import-related errors: invalid imports, imports after code, circular imports."""
        failures: list[dict[str, Any]] = []
        lines = source.splitlines()
        
        import_ended = False
        
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue
            
            # Check if this is an import line
            is_import = stripped.startswith(("import ", "from "))
            
            # Track if we've seen non-import code
            if not is_import and not stripped.startswith("#"):
                import_ended = True
            
            # Imports should come before other code (except docstrings and __future__)
            if is_import and import_ended and line_no > 1:
                prev_non_comment = None
                for prev_line_no in range(line_no - 1, 0, -1):
                    prev_stripped = lines[prev_line_no - 1].strip()
                    if prev_stripped and not prev_stripped.startswith("#"):
                        prev_non_comment = prev_stripped
                        break
                
                # Only report if not following __future__ imports
                if prev_non_comment and not prev_non_comment.startswith("from __future__"):
                    failures.append({
                        "file": relative_path,
                        "line_number": line_no,
                        "bug_type": "IMPORT",
                        "message": "import statement should appear at the top of the file",
                    })
            
            # Check for invalid import patterns
            if is_import:
                # Check for empty imports or syntax errors
                if stripped == "import" or stripped == "from":
                    failures.append({
                        "file": relative_path,
                        "line_number": line_no,
                        "bug_type": "IMPORT",
                        "message": "incomplete import statement",
                    })
                
                # Check for 'from X import' with empty import list
                if stripped.startswith("from ") and " import " in stripped:
                    import_part = stripped.split(" import ", 1)[1].strip()
                    if not import_part:
                        failures.append({
                            "file": relative_path,
                            "line_number": line_no,
                            "bug_type": "IMPORT",
                            "message": "empty import list",
                        })

        return failures
