"""Multi-language patch applier - routes fixes to language-specific patchers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.patch_applier import PatchApplierService
from app.services.java_patch_applier import JavaPatchApplierService
from app.services.javascript_patch_applier import JavaScriptPatchApplierService
from app.services.typescript_patch_applier import TypeScriptPatchApplierService


class MultiLanguagePatchApplierService:
    """Apply fixes for bugs in multiple languages (Python, Java, JavaScript, TypeScript)."""

    def __init__(self) -> None:
        self.python_patcher = PatchApplierService()
        self.java_patcher = JavaPatchApplierService()
        self.javascript_patcher = JavaScriptPatchApplierService()
        self.typescript_patcher = TypeScriptPatchApplierService()

    def apply_fix(
        self,
        repo_path: Path,
        file_path: str,
        line_number: int,
        bug_type: str,
        message: str,
    ) -> bool:
        """Apply a single fix based on the file type."""
        full_path = repo_path / file_path
        
        # Determine language from file extension
        if file_path.endswith(".py"):
            return self.python_patcher.apply_fix(repo_path, file_path, line_number, bug_type, message)
        elif file_path.endswith(".java"):
            # For Java, we need to convert to the batch API
            failure = {
                "file": file_path,
                "line_number": line_number,
                "bug_type": bug_type,
                "message": message,
            }
            result = self.java_patcher.apply_fixes(repo_path, [failure])
            return result["fixed"] > 0
        elif file_path.endswith(".js") and not file_path.endswith(".ts"):
            # JavaScript only (not TypeScript)
            failure = {
                "file": file_path,
                "line_number": line_number,
                "bug_type": bug_type,
                "message": message,
            }
            result = self.javascript_patcher.apply_fixes(repo_path, [failure])
            return result["fixed"] > 0
        elif file_path.endswith(".ts"):
            # TypeScript
            failure = {
                "file": file_path,
                "line_number": line_number,
                "bug_type": bug_type,
                "message": message,
            }
            result = self.typescript_patcher.apply_fixes(repo_path, [failure])
            return result["fixed"] > 0
        
        # Fallback to Python patcher
        return self.python_patcher.apply_fix(repo_path, file_path, line_number, bug_type, message)

    def apply_fixes_batch(
        self,
        repo_path: Path,
        failures: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Apply multiple fixes by language."""
        results = {"python": 0, "java": 0, "javascript": 0, "typescript": 0}
        
        # Group failures by language
        by_lang = {"python": [], "java": [], "javascript": [], "typescript": []}
        
        for failure in failures:
            file_path = failure["file"]
            if file_path.endswith(".py"):
                by_lang["python"].append(failure)
            elif file_path.endswith(".java"):
                by_lang["java"].append(failure)
            elif file_path.endswith(".ts"):
                by_lang["typescript"].append(failure)
            elif file_path.endswith(".js"):
                by_lang["javascript"].append(failure)
        
        # Apply fixes by language
        if by_lang["python"]:
            # Convert to batch format if needed
            for failure in by_lang["python"]:
                applied = self.python_patcher.apply_fix(
                    repo_path,
                    failure["file"],
                    failure["line_number"],
                    failure["bug_type"],
                    failure["message"],
                )
                if applied:
                    results["python"] += 1
        
        if by_lang["java"]:
            result = self.java_patcher.apply_fixes(repo_path, by_lang["java"])
            results["java"] = result["fixed"]
        
        if by_lang["javascript"]:
            result = self.javascript_patcher.apply_fixes(repo_path, by_lang["javascript"])
            results["javascript"] = result["fixed"]
        
        if by_lang["typescript"]:
            result = self.typescript_patcher.apply_fixes(repo_path, by_lang["typescript"])
            results["typescript"] = result["fixed"]
        
        total_fixed = sum(results.values())
        results["total"] = total_fixed
        return results
