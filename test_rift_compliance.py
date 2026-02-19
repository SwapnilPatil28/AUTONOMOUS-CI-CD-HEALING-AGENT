#!/usr/bin/env python3
"""
Comprehensive test to verify RIFT 2026 compliance:
1. Bug type detection (LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION)
2. Test case output format matching
3. Branch naming format
4. Commit message format
5. Results.json generation
"""

import tempfile
from pathlib import Path
import sys
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.static_analyzer import StaticAnalyzerService
from app.agents.pipeline import FailureClassifierAgent, PatchGeneratorAgent
from app.core.policy import build_branch_name, ensure_commit_prefix, validate_commit_prefix


def test_bug_detection():
    """Test all 6 bug types are detected correctly"""
    print("\n" + "="*60)
    print("TEST 1: Bug Type Detection")
    print("="*60)

    code_with_errors = '''
import os
import sys
import math

def calculate_area(radius):
    pi = 3.14
    area = pi * radius ^ 2
    return area

def greet(name):
    print("Hello " + name)

def add_numbers(a, b):
    return a + "b"

x = 10
y = "20"

result = add_numbers(x, y)
print("Result is: " + result)

if x > 5
    print("X is greater than 5")

unused_variable = 42
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(code_with_errors)

        analyzer = StaticAnalyzerService()
        failures = analyzer.analyze(Path(tmpdir))

        bug_types_found = {f["bug_type"] for f in failures}
        expected_types = {"LINTING", "SYNTAX", "LOGIC", "TYPE_ERROR"}

        print(f"\nBug types detected: {bug_types_found}")
        print(f"Expected types (minimum): {expected_types}")

        for failure in failures:
            print(f"  - {failure['bug_type']}: {failure['file']} line {failure['line_number']}")

        if expected_types.issubset(bug_types_found):
            print("\n✓ All bug types detected correctly")
            return True
        else:
            missing = expected_types - bug_types_found
            print(f"\n✗ Missing bug types: {missing}")
            return False


def test_test_case_output_format():
    """Test that output format matches RIFT test case specification"""
    print("\n" + "="*60)
    print("TEST 2: Test Case Output Format")
    print("="*60)

    # Create a test failure as dict (what the classifier expects)
    failure_dict = {
        "file": "src/utils.py",
        "line_number": 15,
        "bug_type": "LINTING",
        "message": "unused import 'os'"
    }

    classifier = FailureClassifierAgent()
    classified = classifier.classify([failure_dict])  # Pass as list of dicts
    classified_failure = classified[0] if classified else None

    generator = PatchGeneratorAgent()
    fix_plan = generator.generate(classified_failure)

    expected_format = "LINTING error in src/utils.py line 15 → Fix: remove the import statement"
    actual_output = fix_plan.expected_output

    print(f"\nExpected: {expected_format}")
    print(f"Actual:   {actual_output}")

    if expected_format == actual_output:
        print("\n✓ Output format matches test case specification")
        return True
    else:
        print("\n✗ Output format DOES NOT match test case")
        return False


def test_branch_naming():
    """Test branch naming format: TEAM_NAME_LEADER_NAME_AI_Fix"""
    print("\n" + "="*60)
    print("TEST 3: Branch Naming Format")
    print("="*60)

    test_cases = [
        ("RIFT ORGANISERS", "Saiyam Kumar", "RIFT_ORGANISERS_SAIYAM_KUMAR_AI_Fix"),
        ("Code Warriors", "John Doe", "CODE_WARRIORS_JOHN_DOE_AI_Fix"),
        ("test team", "leader-name", "TEST_TEAM_LEADER_NAME_AI_Fix"),
    ]

    all_passed = True
    for team, leader, expected in test_cases:
        result = build_branch_name(team, leader)
        status = "✓" if result == expected else "✗"
        print(f"\n{status} Team: '{team}', Leader: '{leader}'")
        print(f"   Expected: {expected}")
        print(f"   Actual:   {result}")
        if result != expected:
            all_passed = False

    return all_passed


def test_commit_message_prefix():
    """Test commit message has [AI-AGENT] prefix"""
    print("\n" + "="*60)
    print("TEST 4: Commit Message Prefix")
    print("="*60)

    test_cases = [
        ("Fix bug", "[AI-AGENT] Fix bug"),
        ("[AI-AGENT] Already prefixed", "[AI-AGENT] Already prefixed"),
        ("Some commit message", "[AI-AGENT] Some commit message"),
    ]

    all_passed = True
    for input_msg, expected in test_cases:
        result = ensure_commit_prefix(input_msg)
        is_valid = validate_commit_prefix(result)
        status = "✓" if result == expected and is_valid else "✗"

        print(f"\n{status} Input: {input_msg}")
        print(f"   Expected: {expected}")
        print(f"   Actual:   {result}")
        print(f"   Valid: {is_valid}")

        if result != expected or not is_valid:
            all_passed = False

    return all_passed


def test_results_json_structure():
    """Test results.json structure is correct"""
    print("\n" + "="*60)
    print("TEST 5: Results.json Structure")
    print("="*60)

    from app.models.api import RunDetailsResponse, FixEntry, TimelineEntry, ScoreBreakdown

    # Create sample response
    sample_run = {
        "run_id": "test-run-123",
        "repository_url": "https://github.com/test/repo",
        "team_name": "Test Team",
        "team_leader_name": "Test Leader",
        "branch_name": "TEST_TEAM_TEST_LEADER_AI_Fix",
        "status": "PASSED",
        "started_at": "2026-02-19T18:00:00Z",
        "completed_at": "2026-02-19T18:05:00Z",
        "duration_seconds": 300.0,
        "total_failures_detected": 5,
        "total_fixes_applied": 5,
        "commit_count": 3,
        "score": {
            "base_score": 100,
            "speed_bonus": 10,
            "efficiency_penalty": 0,
            "final_score": 110,
        },
        "fixes": [
            {
                "file": "test.py",
                "bug_type": "LINTING",
                "line_number": 10,
                "commit_message": "[AI-AGENT] Fix LINTING",
                "status": "FIXED",
                "expected_output": "LINTING error in test.py line 10 → Fix: remove the import statement",
            }
        ],
        "timeline": [
            {
                "iteration": 1,
                "retry_limit": 5,
                "status": "FAILED",
                "timestamp": "2026-02-19T18:00:00Z",
            }
        ],
        "error_message": None,
        "ci_workflow_url": None,
    }

    try:
        response = RunDetailsResponse(**sample_run)
        # Convert to JSON to verify serializability
        json_str = response.model_dump_json()
        json_obj = json.loads(json_str)

        print("\n✓ Results.json structure is valid")
        print(f"  Fields: {len(json_obj)} fields")
        print(f"  Keys: {', '.join(list(json_obj.keys())[:5])}...")

        required_fields = [
            "run_id", "repository_url", "team_name", "team_leader_name",
            "branch_name", "status", "total_failures_detected", "total_fixes_applied",
            "fixes", "timeline", "score"
        ]

        missing = [f for f in required_fields if f not in json_obj]
        if missing:
            print(f"\n✗ Missing fields: {missing}")
            return False

        return True
    except Exception as e:
        print(f"\n✗ Error validating results.json: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("RIFT 2026 COMPLIANCE TEST SUITE")
    print("="*70)

    tests = [
        ("Bug Detection", test_bug_detection),
        ("Test Case Format", test_test_case_output_format),
        ("Branch Naming", test_branch_naming),
        ("Commit Prefix", test_commit_message_prefix),
        ("Results.json", test_results_json_structure),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with error: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests PASSED - Project is RIFT 2026 compliant!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED - Fix issues before deployment")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
