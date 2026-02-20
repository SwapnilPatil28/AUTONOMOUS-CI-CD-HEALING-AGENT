"""Multi-language static analyzer - routes to language-specific analyzers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.static_analyzer import StaticAnalyzerService
from app.services.java_analyzer import JavaAnalyzerService
from app.services.javascript_analyzer import JavaScriptAnalyzerService
from app.services.typescript_analyzer import TypeScriptAnalyzerService


class MultiLanguageAnalyzerService:
    """Analyze source code in multiple languages (Python, Java, JavaScript, TypeScript)."""

    def __init__(self) -> None:
        self.python_analyzer = StaticAnalyzerService()
        self.java_analyzer = JavaAnalyzerService()
        self.javascript_analyzer = JavaScriptAnalyzerService()
        self.typescript_analyzer = TypeScriptAnalyzerService()

    def analyze(self, repo_path: Path) -> list[dict[str, Any]]:
        """Analyze all supported language files in the repository."""
        failures: list[dict[str, Any]] = []
        
        # Analyze Python files
        failures.extend(self.python_analyzer.analyze(repo_path))
        
        # Analyze Java files
        failures.extend(self.java_analyzer.analyze(repo_path))
        
        # Analyze JavaScript files
        failures.extend(self.javascript_analyzer.analyze(repo_path))
        
        # Analyze TypeScript files
        failures.extend(self.typescript_analyzer.analyze(repo_path))
        
        return failures
