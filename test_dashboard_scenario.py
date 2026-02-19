#!/usr/bin/env python3
"""
Comprehensive test simulating the dashboard scenario that was failing.
Tests multi-file, multi-import removal with runner-like behavior.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.patch_applier import PatchApplierService
from app.services.static_analyzer import StaticAnalyzerService


def test_dashboard_scenario():
    """Simulate the exact scenario from the dashboard that was failing."""
    
    test_dir = Path("./test_dashboard_simulation")
    test_dir.mkdir(exist_ok=True)
    
    # Create test files similar to the dashboard failure case
    
    # File 1: config.py with multiple unused imports (lines 1, 2, 3, 4, 5)
    config_content = """import os
import sys
from pathlib import Path
from typing import Any, Dict, List
import json
from collections import defaultdict

# Only using Dict and json
def get_config() -> Dict:
    return json.loads('{}')
"""
    
    # File 2: utils.py with mixed failures
    utils_content = """from typing import Optional
import math
import random

def calculate(x: int) -> Optional[int]:
    return x * 2
"""
    
    config_file = test_dir / "config.py"
    utils_file = test_dir / "utils.py"
    
    config_file.write_text(config_content)
    utils_file.write_text(utils_content)
    
    print("=" * 70)
    print("DASHBOARD SCENARIO TEST")
    print("=" * 70)
    
    # Step 1: Analyze all files
    analyzer = StaticAnalyzerService()
    failures = analyzer.analyze(test_dir)
    
    linting_failures = [f for f in failures if f["bug_type"] == "LINTING"]
    
    print(f"\n{'=' * 70}")
    print(f"STEP 1: STATIC ANALYSIS")
    print(f"{'=' * 70}")
    print(f"Total failures detected: {len(failures)}")
    print(f"LINTING failures: {len(linting_failures)}")
    
    print(f"\n{' ' * 10}File            Line    Message")
    print(f"{' ' * 10}{'-' * 45}")
    for f in sorted(linting_failures, key=lambda x: (x["file"], x["line_number"])):
        print(f"{' ' * 10}{f['file']:<15} {f['line_number']:<7} {f['message']}")
    
    # Step 2: Deduplicate (runner behavior)
    seen_fixes = {}
    for f in linting_failures:
        fix_key = (f["file"], f["line_number"], f["bug_type"])
        if fix_key not in seen_fixes:
            seen_fixes[fix_key] = f
    
    deduplicated = list(seen_fixes.values())
    
    print(f"\n{'=' * 70}")
    print(f"STEP 2: DEDUPLICATION")
    print(f"{'=' * 70}")
    print(f"Before: {len(linting_failures)} failures")
    print(f"After:  {len(deduplicated)} unique fixes")
    
    # Step 3: Group by file and sort descending (runner behavior)
    fixes_by_file = {}
    for f in deduplicated:
        if f["file"] not in fixes_by_file:
            fixes_by_file[f["file"]] = []
        fixes_by_file[f["file"]].append(f)
    
    for file_fixes in fixes_by_file.values():
        file_fixes.sort(key=lambda x: x["line_number"], reverse=True)
    
    sorted_failures = []
    for file_fixes in fixes_by_file.values():
        sorted_failures.extend(file_fixes)
    
    print(f"\n{'=' * 70}")
    print(f"STEP 3: SORT BY LINE (DESCENDING)")
    print(f"{'=' * 70}")
    print(f"Fix order:")
    for i, f in enumerate(sorted_failures, 1):
        print(f"  {i}. {f['file']} line {f['line_number']}")
    
    # Step 4: Apply fixes
    print(f"\n{'=' * 70}")
    print(f"STEP 4: APPLY FIXES")
    print(f"{'=' * 70}")
    
    applier = PatchApplierService()
    fixed = 0
    failed = 0
    
    for f in sorted_failures:
        result = applier.apply_fix(
            repo_path=test_dir,
            file_path=f["file"],
            line_number=f["line_number"],
            bug_type=f["bug_type"],
            message=f["message"]
        )
        status = "✓ FIXED" if result else "✗ FAILED"
        print(f"  {f['file']} line {f['line_number']}: {status}")
        
        if result:
            fixed += 1
        else:
            failed += 1
    
    # Step 5: Show results
    print(f"\n{'=' * 70}")
    print(f"FINAL RESULTS")
    print(f"{'=' * 70}")
    print(f"Fixed:  {fixed}/{len(sorted_failures)}")
    print(f"Failed: {failed}/{len(sorted_failures)}")
    
    # Verify final code
    config_final = config_file.read_text()
    utils_final = utils_file.read_text()
    
    print(f"\n{'=' * 70}")
    print(f"FINAL CODE - config.py")
    print(f"{'=' * 70}")
    print(config_final)
    
    print(f"\n{'=' * 70}")
    print(f"FINAL CODE - utils.py")
    print(f"{'=' * 70}")
    print(utils_final)
    
    # Verify correctness
    print(f"\n{'=' * 70}")
    print(f"VALIDATION")
    print(f"{'=' * 70}")
    
    checks = {
        "config.py: Kept 'import json'": "import json" in config_final,
        "config.py: Kept 'from typing import Dict'": "from typing import Dict" in config_final,
        "config.py: Removed 'import os'": "import os" not in config_final,
        "config.py: Removed 'import sys'": "import sys" not in config_final,
        "config.py: Removed 'from pathlib import Path'": "from pathlib import Path" not in config_final,
        "config.py: Removed 'from collections import defaultdict'": "from collections import defaultdict" not in config_final,
        "utils.py: Kept 'from typing import Optional'": "from typing import Optional" in utils_final,
        "utils.py: Removed 'import math'": "import math" not in utils_final,
        "utils.py: Removed 'import random'": "import random" not in utils_final,
    }
    
    all_passed = True
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check}")
        if not result:
            all_passed = False
    
    # Clean up
    import shutil
    shutil.rmtree(test_dir)
    
    print(f"\n{'=' * 70}")
    if all_passed and failed == 0:
        print("✓✓✓ ALL CHECKS PASSED - DASHBOARD SCENARIO FIXED ✓✓✓")
    else:
        print("✗✗✗ SOME CHECKS FAILED ✗✗✗")
    print(f"{'=' * 70}\n")
    
    return all_passed and failed == 0


if __name__ == "__main__":
    success = test_dashboard_scenario()
    sys.exit(0 if success else 1)
