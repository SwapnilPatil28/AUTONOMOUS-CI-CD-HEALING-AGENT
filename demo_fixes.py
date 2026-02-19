#!/usr/bin/env python
"""
Demo: Show patch applier handling all 6 bug types.
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.patch_applier import PatchApplierService

def main():
    test_file = Path(__file__).parent / "test_sample_broken.py"
    test_dir = test_file.parent
    
    original = """import nonexistingmodule  # LINTING: unused import
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
"""
    
    test_file.write_text(original)
    
    print("=" * 70)
    print("BEFORE PATCHES")
    print("=" * 70)
    print(original)
    
    service = PatchApplierService()
    
    # Fixes with their ORIGINAL line numbers (before any changes)
    fixes = [
        (1, "LINTING", "unused import"),
        (4, "SYNTAX", "missing colon"),
        (10, "INDENTATION", "expected indent"),
        (13, "TYPE_ERROR", "can only concatenate"),
        (19, "TYPE_ERROR", "unsupported operand"),
        (22, "SYNTAX", "missing colon"),
    ]
    
    applied = []
    lines_removed = 0
    
    for original_line, bug_type, msg in fixes:
        # Recalculate current line: original line - offset for removed lines
        current_line = original_line - lines_removed
        
        current_content = test_file.read_text()
        lines = current_content.splitlines()
        
        if current_line < 1 or current_line > len(lines):
            print(f"✗ {bug_type:12} (was line {original_line}, calc {current_line}): Out of range (have {len(lines)} lines)")
            continue
        
        result = service.apply_fix(test_dir, test_file.name, current_line, bug_type, msg)
        if result:
            applied.append(bug_type)
            # Check if this fix actually removed a line (like LINTING)
            new_content = test_file.read_text()
            if len(new_content.splitlines()) < len(lines):
                lines_removed += 1
            print(f"✓ {bug_type:12} (was line {original_line}, now {current_line}): Applied")
        else:
            print(f"✗ {bug_type:12} (was line {original_line}, now {current_line}): Failed")
    
    print("\n" + "=" * 70)
    print(f"AFTER PATCHES ({len(applied)}/6 successfully applied)")
    print("=" * 70)
    after = test_file.read_text()
    print(after)
    
    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)
    checks = [
        ("LINTING applied", "import math" in after and "nonexistingmodule" not in after),
        ("SYNTAX applied (def)", "def calculate_area(radius):" in after),
        ("INDENTATION applied", "    print(\"Hello\"" in after),
        ("TYPE_ERROR wrapping", "str(" in after),
        ("SYNTAX applied (if)", "if x > 5:" in after),
    ]
    
    for check_name, check_result in checks:
        status = "✓" if check_result else "✗"
        print(f"{status} {check_name}")

if __name__ == "__main__":
    main()

