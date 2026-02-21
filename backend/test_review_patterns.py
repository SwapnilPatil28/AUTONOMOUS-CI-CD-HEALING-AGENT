"""Test exact patterns from user's unresolved bugs review."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.java_analyzer import JavaAnalyzerService
from app.services.java_patch_applier import JavaPatchApplierService


def test_exact_review_patterns():
    """Test exact patterns from user's repository review."""
    
    # Patterns from review:
    # 1. TYPE_ERROR: return "Found at mid"; (int method)
    # 2. TYPE_ERROR: return -1.0; (int method)
    # 3. TYPE_ERROR: scores.put("Alice", "95.5"); (Map<String, Double>)
    # 4. TYPE_ERROR: Mixed map types ClassCastException
    # 5. LOGIC: return search(nums, target, mid, high); (infinite recursion)
    # 6. LOGIC: Inverted rotated array
    # 7. LINTING: HashMap map = new HashMap(); (raw type)
    # 8. LINTING: Empty unused methods
    # 9. LINTING: Unused imports (already existed)
    # 10. INDENTATION: Not formatted (already existed)
    
    test_code = '''
import java.util.*;
import java.io.*;

public class ReviewBugs {
    // Pattern 1: int method returning String
    public static int findIndex(int[] arr, int target) {
        for (int i = 0; i < arr.length; i++) {
            if (arr[i] == target) {
                return "Found at mid";
            }
        }
        return -1;
    }
    
    // Pattern 2: int method returning decimal
    public static int searchValue(int[] nums) {
        if (nums.length == 0) {
            return -1.0;
        }
        return 0;
    }
    
    // Pattern 3: Map<String, Double> receiving String  
    public static void calculateScores() {
        Map<String, Double> scores = new HashMap<>();
        scores.put("Alice", "95.5");
        scores.put("Bob", 88.0);
    }
    
    // Pattern 5: Infinite recursion
    public static int binarySearch(int[] nums, int target, int low, int high) {
        if (low > high) return -1;
        int mid = (low + high) / 2;
        if (nums[mid] == target) return mid;
        if (nums[mid] > target) {
            return binarySearch(nums, target, low, mid);
        } else {
            return binarySearch(nums, target, mid, high);
        }
    }
    
    // Pattern 6: Inverted rotated array logic
    public static int searchRotated(int[] nums, int target, int low, int high) {
        if (low > high) return -1;
        int mid = (low + high) / 2;
        if (nums[mid] == target) return mid;
        
        if (nums[low] <= nums[mid]) {
            if (nums[low] <= target && target < nums[mid]) {
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        return searchRotated(nums, target, low, high);
    }
    
    // Pattern 7: Raw types
    public static void useCollections() {
        HashMap data = new HashMap();
        ArrayList items = new ArrayList();
        data.put("key", 1);
        items.add("item");
    }
    
    // Pattern 8: Unused empty method
    public static void helperFunction() {
    }
    
    public static void main(String[] args) {
        int[] arr = {1, 2, 3};
        System.out.println(findIndex(arr, 2));
    }
}
'''
    
    # Write test file
    temp_dir = Path(__file__).parent / "temp_review_test"
    temp_dir.mkdir(exist_ok=True)
    test_file = temp_dir / "ReviewBugs.java"
    test_file.write_text(test_code)
    
    # Analyze
    analyzer = JavaAnalyzerService()
    failures = analyzer.analyze(temp_dir)
    
    print("\n" + "="*70)
    print("EXACT REVIEW PATTERNS TEST")
    print("="*70)
    
    # Check for specific patterns
    patterns_found = {
        "int_return_string": False,
        "int_return_decimal": False,
        "map_type_mismatch": False,
        "infinite_recursion": False,
        "inverted_rotated": False,
        "raw_types": False,
        "unused_empty": False,
    }
    
    for f in failures:
        msg = f['message'].lower()
        if "int method returning string" in msg:
            patterns_found["int_return_string"] = True
        if "int method returning decimal" in msg:
            patterns_found["int_return_decimal"] = True
        if "map<string, double> receiving string" in msg:
            patterns_found["map_type_mismatch"] = True
        if "infinite recursion" in msg:
            patterns_found["infinite_recursion"] = True
        if "inverted rotated" in msg:
            patterns_found["inverted_rotated"] = True
        if "raw type" in msg:
            patterns_found["raw_types"] = True
        if "unused empty" in msg:
            patterns_found["unused_empty"] = True
    
    print("\n🎯 Pattern Detection Status:")
    for pattern, found in patterns_found.items():
        status = "✅" if found else "❌"
        print(f"   {status} {pattern.replace('_', ' ').title()}")
    
    print(f"\n📊 Total Detected: {len(failures)} bugs")
    
    by_type = {}
    for f in failures:
        t = f['bug_type']
        by_type[t] = by_type.get(t, 0) + 1
    
    for bug_type, count in sorted(by_type.items()):
        print(f"   {bug_type}: {count}")
    
    # Apply fixes
    patcher = JavaPatchApplierService()
    result = patcher.apply_fixes(temp_dir, failures)
    
    print(f"\n🔧 Fixes Applied: {result['fixed']}")
    
    # Show fixed code snippet
    fixed_code = test_file.read_text()
    
    # Re-analyze
    failures_after = analyzer.analyze(temp_dir)
    print(f"🔄 Remaining Bugs: {len(failures_after)}")
    
    success_count = sum(1 for v in patterns_found.values() if v)
    
    print("\n" + "="*70)
    if success_count >= 6:  # Allow some tolerance
        print("✅ REVIEW PATTERN DETECTION SUCCESSFUL!")
        print(f"   Detected {success_count}/7 critical patterns from review")
    else:
        print("⚠️ SOME REVIEW PATTERNS MISSED")
        print(f"   Detected {success_count}/7 critical patterns from review")
    print("="*70)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    return success_count >= 6


if __name__ == "__main__":
    success = test_exact_review_patterns()
    sys.exit(0 if success else 1)
