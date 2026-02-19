from __future__ import annotations

import re
from typing import Any

BUG_TYPES = ["LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR", "IMPORT", "INDENTATION"]


class FailureParserService:
    def parse(self, output: str) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        lines = output.splitlines()

        lint_pattern = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s*(?P<code>[A-Z]\d+)\s+(?P<msg>.+)$")
        file_line_pattern = re.compile(r"File \"(?P<file>.+?)\", line (?P<line>\d+)")

        for line in lines:
            lint_match = lint_pattern.match(line.strip())
            if lint_match:
                code = lint_match.group("code")
                msg = lint_match.group("msg")
                bug_type = "LINTING"
                if "import" in msg.lower() and code in {"F401", "E402"}:
                    bug_type = "IMPORT"
                failures.append(
                    {
                        "file": lint_match.group("file"),
                        "line_number": int(lint_match.group("line")),
                        "bug_type": bug_type,
                        "message": msg,
                    }
                )
                continue

            if "SyntaxError" in line or "missing ':'" in line.lower():
                fallback = self._latest_file_line(lines, file_line_pattern)
                failures.append(
                    {
                        "file": fallback[0],
                        "line_number": fallback[1],
                        "bug_type": "SYNTAX",
                        "message": line.strip(),
                    }
                )
                continue

            if "IndentationError" in line or "unexpected indent" in line.lower():
                fallback = self._latest_file_line(lines, file_line_pattern)
                failures.append(
                    {
                        "file": fallback[0],
                        "line_number": fallback[1],
                        "bug_type": "INDENTATION",
                        "message": line.strip(),
                    }
                )
                continue

            if "ModuleNotFoundError" in line or "ImportError" in line:
                fallback = self._latest_file_line(lines, file_line_pattern)
                failures.append(
                    {
                        "file": fallback[0],
                        "line_number": fallback[1],
                        "bug_type": "IMPORT",
                        "message": line.strip(),
                    }
                )
                continue

            if "TypeError" in line:
                fallback = self._latest_file_line(lines, file_line_pattern)
                failures.append(
                    {
                        "file": fallback[0],
                        "line_number": fallback[1],
                        "bug_type": "TYPE_ERROR",
                        "message": line.strip(),
                    }
                )
                continue

        if not failures and "failed" in output.lower():
            failures.append(
                {
                    "file": "unknown",
                    "line_number": 1,
                    "bug_type": "LOGIC",
                    "message": "Test assertion failed",
                }
            )

        deduped: dict[tuple[str, int, str], dict[str, Any]] = {}
        for item in failures:
            if item["bug_type"] not in BUG_TYPES:
                continue
            key = (item["file"], item["line_number"], item["bug_type"])
            deduped[key] = item
        return list(deduped.values())

    def _latest_file_line(self, lines: list[str], pattern: re.Pattern[str]) -> tuple[str, int]:
        for line in reversed(lines):
            match = pattern.search(line)
            if match:
                return match.group("file"), int(match.group("line"))
        return "unknown", 1
