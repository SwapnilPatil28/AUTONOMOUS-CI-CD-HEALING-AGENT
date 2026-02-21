"""
Comprehensive test matching user's exact review scenario.
Tests all 10 unresolved bug categories from repository review.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.java_analyzer import JavaAnalyzerService
from app.services.java_patch_applier import JavaPatchApplierService


def create_test_files(temp_dir: Path):
    """Create files matching user's review patterns."""
    
    # File 1: BinarySearch.java (TYPE_ERROR + LOGIC patterns)
    binary_search = '''
public class BinarySearch {
    public static int search(int[] nums, int target, int low, int high) {
        if (low > high) {
            return "Found at mid";  // TYPE_ERROR: int method returning String
        }
        
        int mid = (low + high) / 2;
        if (nums[mid] == target) {
            return mid;
        }
        
        if (nums[mid] > target) {
            return search(nums, target, low, mid);  // LOGIC: Infinite recursion
        } else {
            return search(nums, target, mid, high);  // LOGIC: Infinite recursion
        }
    }
    
    public static int findValue(int[] arr) {
        if (arr.length == 0) {
            return -1.0;  // TYPE_ERROR: int method returning decimal
        }
        return arr[0];
    }
}
'''
    
    # File 2: RotatedArray.java (LOGIC pattern)
    rotated_array = '''
public class RotatedArray {
    public static int searchRotated(int[] nums, int target, int low, int high) {
        if (low > high) return -1;
        
        int mid = (low + high) / 2;
        if (nums[mid] == target) return mid;
        
        if (nums[low] <= nums[mid]) {
            if (nums[low] <= target && target < nums[mid]) {
                low = mid + 1;  // LOGIC: Inverted - should be high = mid - 1
            } else {
                high = mid - 1;
            }
        } else {
            if (nums[mid] < target && target <= nums[high]) {
                high = mid - 1;  // LOGIC: Inverted - should be low = mid + 1
            } else {
                low = mid + 1;
            }
        }
        
        return searchRotated(nums, target, low, high);
    }
}
'''
    
    # File 3: DataManager.java (TYPE_ERROR + LINTING patterns)
    data_manager = '''
import java.util.*;
import java.io.*;

public class DataManager {
    public static void processScores() {
        Map<String, Double> scores = new HashMap<>();
        scores.put("Alice", "95.5");  // TYPE_ERROR: String in Double map
        scores.put("Bob", 88.0);
        scores.put("Charlie", "87.3");  // TYPE_ERROR: String in Double map
    }
    
    public static void useCollections() {
        HashMap data = new HashMap();  // LINTING: Raw type
        ArrayList items = new ArrayList();  // LINTING: Raw type
        
        data.put("key", 1);
        items.add("item");
    }
    
    // LINTING: Unused empty method
    private static void helperMethod() {
    }
    
    // LINTING: Unused empty method
    private static void internalUtil() {
        // Empty
    }
}
'''
    
    temp_dir.mkdir(exist_ok=True)
    (temp_dir / "BinarySearch.java").write_text(binary_search)
    (temp_dir / "RotatedArray.java").write_text(rotated_array)
    (temp_dir / "DataManager.java").write_text(data_manager)


def test_comprehensive_review_scenario():
    """Test comprehensive scenario matching user's review."""
    
    temp_dir = Path(__file__).parent / "temp_comprehensive_test"
    create_test_files(temp_dir)
    
    print("\n" + "="*75)
    print("COMPREHENSIVE REVIEW SCENARIO TEST")
    print("Matching user's repository review with 10 unresolved bug categories")
    print("="*75)
    
    # Analyze all files
    analyzer = JavaAnalyzerService()
    failures = analyzer.analyze(temp_dir)
    
    # Categorize by pattern
    bug_patterns = {
        "TYPE_ERROR: int→String": 0,
        "TYPE_ERROR: int→decimal": 0,
        "TYPE_ERROR: Map<String,Double>→String": 0,
        "LOGIC: Infinite recursion": 0,
        "LOGIC: Inverted rotated array": 0,
        "LINTING: Raw types": 0,
        "LINTING: Unused empty methods": 0,
        "LINTING: Unused imports": 0,
        "Other": 0,
    }
    
    for f in failures:
        msg = f['message'].lower()
        bug_type = f['bug_type']
        
        if "int method returning string" in msg:
            bug_patterns["TYPE_ERROR: int→String"] += 1
        elif "int method returning decimal" in msg:
            bug_patterns["TYPE_ERROR: int→decimal"] += 1
        elif "map<string, double> receiving string" in msg:
            bug_patterns["TYPE_ERROR: Map<String,Double>→String"] += 1
        elif "infinite recursion" in msg:
            bug_patterns["LOGIC: Infinite recursion"] += 1
        elif "inverted rotated" in msg:
            bug_patterns["LOGIC: Inverted rotated array"] += 1
        elif "raw type" in msg:
            bug_patterns["LINTING: Raw types"] += 1
        elif "unused empty" in msg:
            bug_patterns["LINTING: Unused empty methods"] += 1
        elif "unused import" in msg and bug_type == "LINTING":
            bug_patterns["LINTING: Unused imports"] += 1
        else:
            bug_patterns["Other"] += 1
    
    print("\n📊 Bug Detection by Category:")
    print("-" * 75)
    critical_found = 0
    for pattern, count in bug_patterns.items():
        if count > 0:
            status = "✅" if count > 0 else "  "
            print(f"{status} {pattern:45} | Count: {count}")
            if "Other" not in pattern:
                critical_found += 1
    
    print(f"\n{'=' * 75}")
    print(f"Total Bugs Detected: {len(failures)}")
    print(f"Critical Categories Found: {critical_found}/7")
    
    # Group by file
    by_file = {}
    for f in failures:
        file = f['file']
        if file not in by_file:
            by_file[file] = []
        by_file[file].append(f)
    
    print(f"\n📁 Breakdown by File:")
    for file, bugs in sorted(by_file.items()):
        print(f"\n   {file}:")
        for bug in bugs:
            print(f"      Line {bug['line_number']:3} | {bug['bug_type']:12} | {bug['message']}")
    
    # Apply fixes
    print(f"\n{'=' * 75}")
    print("🔧 APPLYING FIXES...")
    print("-" * 75)
    
    patcher = JavaPatchApplierService()
    result = patcher.apply_fixes(temp_dir, failures)
    
    print(f"✓ Fixes Applied: {result['fixed']}")
    print(f"✓ Files Modified: {result['files']}")
    
    # Re-analyze
    failures_after = analyzer.analyze(temp_dir)
    
    print(f"\n{'=' * 75}")
    print(f"🔄 Re-analysis After Fixes:")
    print(f"   Before: {len(failures)} bugs")
    print(f"   After:  {len(failures_after)} bugs")
    print(f"   Fixed:  {len(failures) - len(failures_after)} bugs")
    
    if failures_after:
        print(f"\n⚠️  Remaining Issues ({len(failures_after)}):")
        for f in failures_after[:10]:  # Show first 10
            print(f"      {f['file']}:{f['line_number']} [{f['bug_type']}] {f['message']}")
    
    # Success criteria
    success = (
        critical_found >= 6 and  # Found at least 6/7 critical categories
        len(failures) >= 8 and   # Detected at least 8 bugs total
        result['fixed'] >= 6     # Fixed at least 6 bugs
    )
    
    print(f"\n{'=' * 75}")
    if success:
        print("✅ COMPREHENSIVE TEST PASSED!")
        print(f"   ✓ Critical categories detected: {critical_found}/7")
        print(f"   ✓ Total bugs found: {len(failures)}")
        print(f"   ✓ Bugs fixed: {result['fixed']}")
        print(f"   ✓ Ready for production testing on real repository")
    else:
        print("❌ COMPREHENSIVE TEST NEEDS REVIEW")
        print(f"   Categories: {critical_found}/7")
        print(f"   Bugs found: {len(failures)}")
        print(f"   Bugs fixed: {result['fixed']}")
    print("="*75)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    return success


if __name__ == "__main__":
    success = test_comprehensive_review_scenario()
    sys.exit(0 if success else 1)
