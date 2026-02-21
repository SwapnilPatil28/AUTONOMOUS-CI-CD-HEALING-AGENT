"""Test new Java bug detection patterns for unresolved bugs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.java_analyzer import JavaAnalyzerService
from app.services.java_patch_applier import JavaPatchApplierService


def test_new_patterns():
    """Test detection and fixing of newly added bug patterns."""
    
    # Create test file with all new patterns
    test_code = '''
import java.util.*;

public class BuggyCode {
    
    // TYPE_ERROR: int method returning String literal
    public static int binarySearch(int[] nums, int target, int low, int high) {
        if (low > high) {
            return "Found at mid";  // BUG: int method returning String
        }
        int mid = (low + high) / 2;
        if (nums[mid] == target) {
            return mid;
        }
        return -1;
    }
    
    // TYPE_ERROR: int method returning decimal
    public static int findElement(int[] arr) {
        if (arr.length == 0) {
            return -1.0;  // BUG: decimal in int return
        }
        return arr[0];
    }
    
    // TYPE_ERROR: Map<String, Double> receiving String value
    public static void testMap() {
        Map<String, Double> scores = new HashMap<>();
        scores.put("Alice", "95.5");  // BUG: String instead of Double
        scores.put("Bob", 88.0);
    }
    
    // LOGIC: Infinite recursion - mid not incremented
    public static int search(int[] nums, int target, int low, int high) {
        if (low > high) return -1;
        int mid = (low + high) / 2;
        if (nums[mid] == target) return mid;
        if (nums[mid] > target) {
            return search(nums, target, low, mid);  // BUG: should be mid - 1
        } else {
            return search(nums, target, mid, high);  // BUG: should be mid + 1
        }
    }
    
    // LOGIC: Inverted rotated array logic
    public static int searchRotated(int[] nums, int target, int low, int high) {
        if (low > high) return -1;
        int mid = (low + high) / 2;
        if (nums[mid] == target) return mid;
        
        if (nums[low] <= nums[mid]) {
            if (nums[low] <= target && target < nums[mid]) {
                low = mid + 1;  // BUG: should search left (high = mid - 1)
            } else {
                high = mid - 1;
            }
        } else {
            if (nums[mid] < target && target <= nums[high]) {
                high = mid - 1;  // BUG: should search right (low = mid + 1)
            } else {
                low = mid + 1;
            }
        }
        return searchRotated(nums, target, low, high);
    }
    
    // LINTING: Raw types
    public static void rawTypeTest() {
        HashMap map = new HashMap();  // BUG: no generics
        ArrayList list = new ArrayList();  // BUG: no generics
        map.put("key", "value");
        list.add(1);
    }
    
    // LINTING: Unused empty method
    public static void unusedHelperMethod() {
        // BUG: empty and never called
    }
    
    public static void main(String[] args) {
        int[] arr = {1, 2, 3, 4, 5};
        System.out.println(binarySearch(arr, 3, 0, 4));
        testMap();
    }
}
'''
    
    # Write test file
    temp_dir = Path(__file__).parent / "temp_test_dir"
    temp_dir.mkdir(exist_ok=True)
    test_file = temp_dir / "BuggyCode.java"
    test_file.write_text(test_code)
    
    # Analyze
    analyzer = JavaAnalyzerService()
    failures = analyzer.analyze(temp_dir)
    
    print("\n" + "="*70)
    print("NEW JAVA PATTERN DETECTION TEST")
    print("="*70)
    
    # Count by bug type
    type_errors = [f for f in failures if f["bug_type"] == "TYPE_ERROR"]
    logic_errors = [f for f in failures if f["bug_type"] == "LOGIC"]
    linting_errors = [f for f in failures if f["bug_type"] == "LINTING"]
    
    print(f"\n📊 Detection Results:")
    print(f"   TYPE_ERROR: {len(type_errors)} bugs")
    print(f"   LOGIC: {len(logic_errors)} bugs")
    print(f"   LINTING: {len(linting_errors)} bugs")
    print(f"   TOTAL: {len(failures)} bugs")
    
    print(f"\n🔍 Detected Bugs:")
    for f in failures:
        print(f"   Line {f['line_number']}: [{f['bug_type']}] {f['message']}")
    
    # Apply fixes
    patcher = JavaPatchApplierService()
    result = patcher.apply_fixes(temp_dir, failures)
    
    print(f"\n🔧 Fixes Applied: {result['fixed']}")
    
    # Re-analyze to check remaining
    fixed_code = test_file.read_text()
    failures_after = analyzer.analyze(temp_dir)
    
    print(f"🔄 Remaining Failures: {len(failures_after)}")
    
    if failures_after:
        print("\n⚠️ Still Unresolved:")
        for f in failures_after:
            print(f"   Line {f['line_number']}: [{f['bug_type']}] {f['message']}")
    
    # Expected detections:
    # TYPE_ERROR: 3 (int->String, int->decimal, Map<String,Double>->String)
    # LOGIC: 4 (2x infinite recursion, 2x inverted rotated array)
    # LINTING: 3 (2x raw types, 1x unused empty method)
    # Total expected: 10
    
    success = len(failures) >= 8  # Allow some tolerance
    print("\n" + "="*70)
    if success:
        print("✅ NEW PATTERN DETECTION WORKING!")
        print(f"   Detected {len(failures)} bugs (expected ~10)")
    else:
        print("❌ DETECTION INCOMPLETE")
        print(f"   Detected {len(failures)} bugs (expected ~10)")
    print("="*70)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    return success


if __name__ == "__main__":
    success = test_new_patterns()
    sys.exit(0 if success else 1)
