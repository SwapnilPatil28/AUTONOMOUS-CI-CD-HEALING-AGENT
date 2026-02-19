from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


class StaticAnalyzerService:
    def analyze(self, repo_path: Path) -> list[dict[str, Any]]:
        """Analyze Python files for errors: syntax, unused imports, unused variables, logic errors."""
        failures: list[dict[str, Any]] = []
        for file_path in self._iter_python_files(repo_path):
            relative_path = file_path.relative_to(repo_path).as_posix()
            source = file_path.read_text(encoding="utf-8", errors="ignore")

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
                continue

            failures.extend(self._find_unused_imports(tree, relative_path))
            failures.extend(self._find_unused_variables(tree, source, relative_path))
            failures.extend(self._find_logic_errors(source, relative_path))
            failures.extend(self._find_type_errors(source, relative_path))

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
            # Pattern: return a + "x" or similar
            if "return" in code and "+" in code:
                # Look for pattern: + "single_char" which is likely a mistake
                if re.search(r'\+\s*["\']\\w["\']', code):
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
        
        for line_no, line in enumerate(lines, start=1):
            code = line.split("#", 1)[0].strip()
            if not code:
                continue
            
            # Track variable assignments to infer types
            assign_match = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)$', code)
            if assign_match:
                var_name = assign_match.group(1)
                value = assign_match.group(2).strip()
                
                # Infer type from literal
                if value.startswith('"') or value.startswith("'"):
                    variable_types[var_name] = "str"
                elif re.match(r'^\d+$', value):
                    variable_types[var_name] = "int"
                elif re.match(r'^\d+\.\d+$', value):
                    variable_types[var_name] = "float"
                elif value.startswith('['):
                    variable_types[var_name] = "list"
            
            # Detect type mismatches in operations
            # Pattern: int_var + "string" or str_var + int_literal
            if "+" in code and "==" not in code and "!=" not in code:
                # Check for operations outside of assignments
                if "=" in code.split("+")[0]:
                    continue  # This is an assignment
                
                # This is likely a concatenation/addition operation
                parts = code.split("+")
                for i in range(len(parts) - 1):
                    left = parts[i].strip().split()[-1] if parts[i].strip() else ""
                    right = parts[i + 1].strip().split()[0] if parts[i + 1].strip() else ""
                    
                    # Check for int + string_literal or string_var + int_var mismatches
                    left_is_string = (left.startswith('"') or left.startswith("'")) or (left in variable_types and variable_types[left] == "str")
                    right_is_string = (right.startswith('"') or right.startswith("'")) or (right in variable_types and variable_types[right] == "str")
                    
                    left_is_int = re.match(r'^\d+$', left) or (left in variable_types and variable_types[left] == "int")
                    right_is_int = re.match(r'^\d+$', right) or (right in variable_types and variable_types[right] == "int")
                    
                    # Mismatch: int + string or string + int
                    if (left_is_int and right_is_string) or (left_is_string and right_is_int):
                        failures.append({
                            "file": relative_path,
                            "line_number": line_no,
                            "bug_type": "TYPE_ERROR",
                            "message": "type mismatch in concatenation/addition: cannot add int and str",
                        })
                        break
        
        return failures

    @staticmethod
    def _find_type_errors(source: str, relative_path: str) -> list[dict[str, Any]]:
        """Find potential type errors: string concatenation with non-strings, int+str."""
        failures: list[dict[str, Any]] = []
        lines = source.splitlines()
        variable_types: dict[str, str] = {}  # name -> inferred type
        
        for line_no, line in enumerate(lines, start=1):
            code = line.split("#", 1)[0].strip()
            if not code:
                continue
            
            # Track variable assignments to infer types
            assign_match = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)$', code)
            if assign_match:
                var_name = assign_match.group(1)
                value = assign_match.group(2).strip()
                
                # Infer type from literal
                if value.startswith('"') or value.startswith("'"):
                    variable_types[var_name] = "str"
                elif re.match(r'^\d+$', value):
                    variable_types[var_name] = "int"
                elif re.match(r'^\d+\.\d+$', value):
                    variable_types[var_name] = "float"
                elif value.startswith('['):
                    variable_types[var_name] = "list"
            
            # Detect type mismatches in operations
            # Pattern: int_var + "string" or str_var + int_literal
            if "+" in code and "=" not in code.split("+")[0]:
                # This is likely a concatenation/addition operation
                parts = code.split("+")
                for i in range(len(parts) - 1):
                    left = parts[i].strip().split()[-1] if parts[i].strip() else ""
                    right = parts[i + 1].strip().split()[0] if parts[i + 1].strip() else ""
                    
                    # Check for int + string_literal or string_var + int_var mismatches
                    left_is_string = (left.startswith('"') or left.startswith("'")) or (left in variable_types and variable_types[left] == "str")
                    right_is_string = (right.startswith('"') or right.startswith("'")) or (right in variable_types and variable_types[right] == "str")
                    
                    left_is_int = re.match(r'^\d+$', left) or (left in variable_types and variable_types[left] == "int")
                    right_is_int = re.match(r'^\d+$', right) or (right in variable_types and variable_types[right] == "int")
                    
                    # Mismatch: int + string or string + int
                    if (left_is_int and right_is_string) or (left_is_string and right_is_int):
                        failures.append({
                            "file": relative_path,
                            "line_number": line_no,
                            "bug_type": "TYPE_ERROR",
                            "message": "type mismatch in concatenation/addition: cannot add int and str",
                        })
                        break
        
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