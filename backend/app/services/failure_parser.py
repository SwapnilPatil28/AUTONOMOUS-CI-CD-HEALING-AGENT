from __future__ import annotations

import re
from typing import Any

BUG_TYPES = ["LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR", "IMPORT", "INDENTATION"]


class FailureParserService:
    """Parse pytest/linter output to extract structured failure information."""
    
    def parse(self, output: str) -> list[dict[str, Any]]:
        """Parse test output and extract failures with file/line/type info."""
        failures: list[dict[str, Any]] = []
        lines = output.splitlines()
        
        # Track the current file/line from traceback context
        current_file = None
        current_line = None
        
        for i, line in enumerate(lines):
            # Extract file/line from traceback "File xxx, line YYY" format
            file_line_match = re.search(r'File "([^"]+)", line (\d+)', line)
            if file_line_match:
                current_file = file_line_match.group(1)
                current_line = int(file_line_match.group(2))
            
            # LINTING: Flake8/pylint format
            lint_match = re.match(r'^([^:\s]+):(\d+):\d+:\s*([A-Z]\d+)\s+(.+)$', line.strip())
            if lint_match:
                failures.append({
                    "file": lint_match.group(1),
                    "line_number": int(lint_match.group(2)),
                    "bug_type": "LINTING",
                    "message": lint_match.group(4),
                })
                continue
            
            # SYNTAX: Parse SyntaxError properly
            if "SyntaxError" in line:
                file_info = self._extract_pytest_file_line(lines, i)
                if file_info:
                    failures.append({
                        "file": file_info[0],
                        "line_number": file_info[1],
                        "bug_type": "SYNTAX",
                        "message": line.strip(),
                    })
                continue
            
            # INDENTATION: Parse IndentationError
            if "IndentationError" in line or "unexpected indent" in line.lower():
                file_info = self._extract_pytest_file_line(lines, i)
                if file_info:
                    failures.append({
                        "file": file_info[0],
                        "line_number": file_info[1],
                        "bug_type": "INDENTATION",
                        "message": line.strip(),
                    })
                continue
            
            # IMPORT: Parse ImportError/ModuleNotFoundError with context
            if "ModuleNotFoundError" in line or "ImportError" in line or "cannot import name" in line.lower():
                file_info = self._extract_pytest_file_line(lines, i)
                if file_info:
                    failures.append({
                        "file": file_info[0],
                        "line_number": file_info[1],
                        "bug_type": "IMPORT",
                        "message": line.strip(),
                    })
                continue
            
            # TYPE_ERROR: Parse TypeError with proper file/line extraction
            if "TypeError" in line:
                file_info = self._extract_pytest_file_line(lines, i)
                if file_info and file_info[0] != "unknown":
                    failures.append({
                        "file": file_info[0],
                        "line_number": file_info[1],
                        "bug_type": "TYPE_ERROR",
                        "message": line.strip(),
                    })
                continue
            
            # LOGIC/ASSERTION: AssertionError or test failure
            if "AssertionError" in line:
                file_info = self._extract_pytest_file_line(lines, i)
                if file_info:
                    failures.append({
                        "file": file_info[0],
                        "line_number": file_info[1],
                        "bug_type": "LOGIC",
                        "message": line.strip(),
                    })
                continue
            
            # LOGIC: Failed test with assertion context
            if re.search(r'^(FAILED|assert|AssertionError)', line.strip(), re.IGNORECASE):
                file_info = self._extract_pytest_file_line(lines, i)
                if file_info:
                    failures.append({
                        "file": file_info[0],
                        "line_number": file_info[1],
                        "bug_type": "LOGIC",
                        "message": line.strip(),
                    })
                    continue
        
        # Deduplicate by (file, line_number, bug_type) tuple
        deduped: dict[tuple[str, int, str], dict[str, Any]] = {}
        for item in failures:
            if item["bug_type"] not in BUG_TYPES:
                continue
            key = (item["file"], item["line_number"], item["bug_type"])
            deduped[key] = item
        
        return list(deduped.values())
    
    def _extract_pytest_file_line(self, lines: list[str], error_line_idx: int) -> tuple[str, int] | None:
        """Extract file and line number from pytest traceback context."""
        # Search backwards from error line for "File xxx, line YYY" pattern
        for i in range(error_line_idx, -1, -1):
            match = re.search(r'File "([^"]+)", line (\d+)', lines[i])
            if match:
                return (match.group(1), int(match.group(2)))
        
        # Also search forward a bit in case next few lines have context
        for i in range(error_line_idx, min(error_line_idx + 3, len(lines))):
            match = re.search(r'File "([^"]+)", line (\d+)', lines[i])
            if match:
                return (match.group(1), int(match.group(2)))
        
        return None
