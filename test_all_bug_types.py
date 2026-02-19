#!/usr/bin/env python3
"""Comprehensive test for all 6 bug types: SYNTAX, LINTING, LOGIC, TYPE_ERROR, IMPORT, INDENTATION"""

import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.static_analyzer import StaticAnalyzerService
from app.services.patch_applier import PatchApplierService


def test_all_bug_types():
    """Test detection and fixing of all 6 bug types."""
    
    test_cases = [
        {
            "name": "SYNTAX - Missing colon",
            "code": "if x > 5\n    print('hello')",
            "bug_type": "SYNTAX",
            "should_detect": True,
            "fix_message": "missing :",
        },
        {
            "name": "LINTING - Unused import",
            "code": "import math\nprint('hello')",
            "bug_type": "LINTING",
            "should_detect": True,
            "fix_message": "unused import",
        },
        {
            "name": "LINTING - Unused variable",
            "code": "x = 10\nprint('hello')",
            "bug_type": "LINTING",
            "should_detect": True,
            "fix_message": "unused variable",
        },
        {
            "name": "LOGIC - XOR should be exponentiation",
            "code": "result = 2 ^ 3",
            "bug_type": "LOGIC",
            "should_detect": True,
            "fix_message": "XOR",
        },
        {
            "name": "LOGIC - String literal instead of variable",
            "code": 'return a + "b"',
            "bug_type": "LOGIC",
            "should_detect": True,
            "fix_message": "string literal",
        },
        {
            "name": "LOGIC - Reversed max comparison",
            "code": "max_value = numbers[0]\nfor num in numbers:\n    if num < max_value:\n        max_value = num",
            "bug_type": "LOGIC",
            "should_detect": True,
            "fix_message": "comparison for max",
        },
        {
            "name": "TYPE_ERROR - int + str",
            "code": 'result = 10\nprint("Result: " + result)',
            "bug_type": "TYPE_ERROR",
            "should_detect": True,
            "fix_message": "type mismatch",
        },
        {
            "name": "TYPE_ERROR - variable + string literal",
            "code": 'x = 10\ny = x + "20"',
            "bug_type": "TYPE_ERROR",
            "should_detect": True,
            "fix_message": "unsupported operand",
        },
        {
            "name": "TYPE_ERROR - str + int variables",
            "code": 'def demo():\n    x = "10"\n    y = 5\n    return x + y',
            "bug_type": "TYPE_ERROR",
            "should_detect": True,
            "fix_message": "type mismatch",
        },
        {
            "name": "TYPE_ERROR - function arg mismatch",
            "code": 'def add_numbers(a: int, b: int) -> int:\n    return a + b\n\nresult = add_numbers("5", 10)',
            "bug_type": "TYPE_ERROR",
            "should_detect": True,
            "fix_message": "argument type mismatch",
        },
        {
            "name": "IMPORT - Imports after code",
            "code": "print('hello')\nimport math",
            "bug_type": "IMPORT",
            "should_detect": True,
            "fix_message": "top of file",
        },
        {
            "name": "INDENTATION - Missing indent after colon",
            "code": "if True:\nprint('hello')",
            "bug_type": "INDENTATION",
            "should_detect": True,
            "fix_message": "indentation",
        },
        {
            "name": "INDENTATION - Mixed tabs and spaces",
            "code": "if True:\n\tprint('hello')",
            "bug_type": "INDENTATION",
            "should_detect": True,
            "fix_message": "tab",
        },
    ]

    analyzer = StaticAnalyzerService()
    applier = PatchApplierService()
    
    print("\n" + "="*70)
    print("COMPREHENSIVE BUG TYPE DETECTION AND FIXING TEST")
    print("="*70)

    detection_pass = 0
    detection_fail = 0
    fix_pass = 0
    fix_fail = 0

    for test_case in test_cases:
        print(f"\n✓ Test: {test_case['name']}")
        print(f"  Code: {repr(test_case['code'][:50])}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(test_case['code'])
            
            # Run analyzer
            failures = analyzer.analyze(Path(tmpdir))
            detected = False
            detected_failure = None
            
            for failure in failures:
                if failure['bug_type'] == test_case['bug_type']:
                    detected = True
                    detected_failure = failure
                    break
            
            if detected:
                print(f"  ✓ DETECTED: {test_case['bug_type']} at line {detected_failure['line_number']}")
                detection_pass += 1
                
                # Try to fix
                fix_result = applier.apply_fix(
                    repo_path=Path(tmpdir),
                    file_path="test.py",
                    line_number=detected_failure['line_number'],
                    bug_type=test_case['bug_type'],
                    message=detected_failure['message']
                )
                
                if fix_result:
                    fixed_code = test_file.read_text()
                    print(f"  ✓ FIXED: Applied fix successfully")
                    print(f"    Before: {repr(test_case['code'][:40])}")
                    print(f"    After:  {repr(fixed_code[:40])}")
                    fix_pass += 1
                else:
                    print(f"  ✗ FIX FAILED: Could not apply fix")
                    fix_fail += 1
            else:
                print(f"  ✗ NOT DETECTED: {test_case['bug_type']} was not found")
                detection_fail += 1
                fix_fail += 1

    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Detection: {detection_pass}/{detection_pass + detection_fail} PASSED")
    print(f"Fixes:     {fix_pass}/{fix_pass + fix_fail} PASSED")
    
    if detection_fail == 0 and fix_fail == 0:
        print("\n✓ ALL TESTS PASSED - Complete coverage of all 6 bug types!")
        return True
    else:
        print(f"\n✗ {detection_fail + fix_fail} TESTS FAILED")
        return False


if __name__ == "__main__":
    success = test_all_bug_types()
    sys.exit(0 if success else 1)
