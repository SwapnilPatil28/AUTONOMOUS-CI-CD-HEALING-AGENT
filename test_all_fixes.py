#!/usr/bin/env python
"""
Single-pass comprehensive test of all 6 bug-type fixes.
Each test fixes its own copy of the broken file to avoid line number changes.
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.patch_applier import PatchApplierService

def create_broken_file(path: Path):
    """Create a fresh broken file."""
    path.write_text("""import nonexistingmodule  # LINTING: unused import
import math

def calculate_area(radius)  # SYNTAX: missing colon
    pi = 3.14
    area = pi * radius ^ 2
    return area

def greet(name):  # INDENTATION: missing indent on next line
print("Hello " + name)

def add_numbers(a, b):
    return a + "b"  # TYPE_ERROR: str + str expected

x = 10
y = "20"

result = add_numbers(x, y)  # TYPE_ERROR: calling with mismatched types
print("Result is: " + result)

if x > 5  # SYNTAX: missing colon
    print("X is greater than 5")

unused_variable = 42  # LINTING: unused variable
""")

def test_fix(bug_type: str, line: int, message: str, expected_in_result: str) -> bool:
    """Test a single fix type."""
    test_file = Path(__file__).parent / f"test_{bug_type.lower()}.py"
    test_dir = test_file.parent
    
    create_broken_file(test_file)
    
    service = PatchApplierService()
    before = test_file.read_text()
    
    result = service.apply_fix(test_dir, test_file.name, line, bug_type, message)
    
    if not result:
        print(f"❌ {bug_type:12} (line {line:2}): FIX FAILED")
        return False
    
    after = test_file.read_text()
    if expected_in_result not in after:
        print(f"❌ {bug_type:12} (line {line:2}): Expected '{expected_in_result}' not in result")
        return False
    
    print(f"✅ {bug_type:12} (line {line:2}): Fixed! ('{expected_in_result[:50]}...' present)")
    return True

def main():
    print("=" * 70)
    print("PATCH APPLIER COMPREHENSIVE TEST - All 6 Bug Types")
    print("=" * 70)
    
    tests = [
        ("LINTING", 1, "unused import", "import math"),
        ("SYNTAX", 4, "missing colon", "def calculate_area(radius):"),
        ("INDENTATION", 10, "expected indent", "    print(\"Hello\""),
        ("TYPE_ERROR", 13, "can only concatenate str", "str(\"b\")"),
        ("TYPE_ERROR", 19, "unsupported operand", "str(result)"),
        ("SYNTAX", 22, "missing colon", "if x > 5:"),
    ]
    
    passed = 0
    failed = 0
    
    for bug_type, line, message, expected in tests:
        if test_fix(bug_type, line, message, expected):
            passed += 1
        else:
            failed += 1
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
