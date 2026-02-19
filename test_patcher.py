"""Test patch applier functionality."""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.patch_applier import PatchApplierService

def test_patches():
    service = PatchApplierService()
    test_file = Path(__file__).parent / "test_sample_broken.py"
    
    print(f"Original file:\n{test_file.read_text()}\n")
    print("=" * 60)
    
    # Test 1: Remove unused import (line 1)
    print("\n[1] Applying LINTING fix (line 1 - remove unused import)...")
    result = service.apply_fix(test_file.parent, "test_sample_broken.py", 1, "LINTING", "unused import")
    print(f"Result: {result}")
    print(f"File now:\n{test_file.read_text()}\n")
    
    # Now recount lines
    lines = test_file.read_text().splitlines()
    
    # Test 2: Fix missing colon on line 3 (def calculate_area - was line 4)
    print("\n[2] Applying SYNTAX fix (line 3 - add colon to def)...")
    result = service.apply_fix(test_file.parent, "test_sample_broken.py", 3, "SYNTAX", "missing colon")
    print(f"Result: {result}")
    print(f"File now:\n{test_file.read_text()}\n")
    
    # Test 3: Fix indentation on line 8 (after greet def - was line 9)
    print("\n[3] Applying INDENTATION fix (line 8 - indent print statement)...")
    result = service.apply_fix(test_file.parent, "test_sample_broken.py", 8, "INDENTATION", "expected an indented block")
    print(f"Result: {result}")
    print(f"File now:\n{test_file.read_text()}\n")
    
    # Test 4: Fix type error on line 12 (a + "b" - was line 13)
    print("\n[4] Applying TYPE_ERROR fix (line 12 - wrap b with str())...")
    result = service.apply_fix(test_file.parent, "test_sample_broken.py", 12, "TYPE_ERROR", "can only concatenate str (not \"str\") to str")
    print(f"Result: {result}")
    print(f"File now:\n{test_file.read_text()}\n")
    
    # Test 5: Fix type error on line 18 (result + string concat - was line 19)
    print("\n[5] Applying TYPE_ERROR fix (line 18 - wrap result with str())...")
    result = service.apply_fix(test_file.parent, "test_sample_broken.py", 18, "TYPE_ERROR", "unsupported operand type(s) for +: 'int' and 'str'")
    print(f"Result: {result}")
    print(f"File now:\n{test_file.read_text()}\n")
    
    # Test 6: Fix missing colon on line 20 (if statement - was line 21)
    print("\n[6] Applying SYNTAX fix (line 20 - add colon to if)...")
    result = service.apply_fix(test_file.parent, "test_sample_broken.py", 20, "SYNTAX", "missing colon")
    print(f"Result: {result}")
    print(f"File now:\n{test_file.read_text()}\n")
    
    print("\n" + "=" * 60)
    print(f"\nFinal file:\n{test_file.read_text()}")

if __name__ == "__main__":
    test_patches()

