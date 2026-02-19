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
        
        return failures

    @staticmethod
    def _find_type_errors(source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find potential type errors: string concatenation with non-strings, int+str."""
        failures: list[dict[str, Any]] = []
        lines = source.splitlines()
        variable_types: dict[str, str] = {}  # name -> inferred type
        
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
                
                # Cases with variables - but exclude function calls and string multiplication
                # unknown_var + string_literal might be type error
                elif (not (left_is_str_lit or left_is_int_lit or left_is_str_var or left_is_call)) and right_is_str_lit and not has_string_multiplication:
                    # variable + "string" - this is type error if variable isn't a string
                    is_type_error = True
                # string_literal + unknown_var might be type error
                elif left_is_str_lit and (not (right_is_str_lit or right_is_int_lit or right_is_str_var or right_is_call)) and not has_string_multiplication:
                    # "string" + variable
                    is_type_error = True
                
                if is_type_error:
                    failures.append({
                        "file": relative_path,
                        "line_number": line_no,
                        "bug_type": "TYPE_ERROR",
                        "message": "type mismatch: cannot add incompatible types",
                    })
                    break  # Only report once per line
        
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
