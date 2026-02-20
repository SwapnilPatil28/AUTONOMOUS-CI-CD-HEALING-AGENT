#!/usr/bin/env python3
"""
Validation test for multi-language support.
Tests Java, JavaScript, and TypeScript bug detection and fixing.
"""

import tempfile
from pathlib import Path
from app.services.multi_language_analyzer import MultiLanguageAnalyzerService
from app.services.multi_language_patch_applier import MultiLanguagePatchApplierService

# Sample code with bugs

JAVA_CODE = """
public class Calculator {
    public int add(int a, int b) {
        int sum = a + b
        return sum
    }
    
    public int remove_item(int count) {
        count += 1;  // WRONG: should be -= for removal
        return count;
    }
}
"""

JAVASCRIPT_CODE = """
const calculate = (numbers) => {
    let sum = 0;
    for (let num of numbers) {
        sum += num
    }
    return sum / 100;  // WRONG: should divide by length
}

class calculator {  // WRONG: should be PascalCase
    getValue() {
        return "Total: " + this.total;  // TYPE_ERROR
    }
}
"""

TYPESCRIPT_CODE = """
import unused from 'unused-module';

interface user_profile {  // WRONG: should be PascalCase
    name: string;
    age: number
}

class BankAccount {
    private balance: number = 0;
    
    deposit(amount: number) {
        this.balance -= amount;  // WRONG: should be +=
    }
}
"""

def test_multi_language_detection():
    """Test that all language analyzers detect bugs correctly."""
    analyzer = MultiLanguageAnalyzerService()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create Java file
        java_file = tmpdir / "Calculator.java"
        java_file.write_text(JAVA_CODE)
        
        # Create JavaScript file
        js_file = tmpdir / "calculator.js"
        js_file.write_text(JAVASCRIPT_CODE)
        
        # Create TypeScript file
        ts_file = tmpdir / "user_profile.ts"
        ts_file.write_text(TYPESCRIPT_CODE)
        
        # Analyze all files
        failures = analyzer.analyze(tmpdir)
        
        print("=" * 70)
        print("MULTI-LANGUAGE BUG DETECTION TEST")
        print("=" * 70)
        
        # Group by language
        by_lang = {}
        for failure in failures:
            lang = failure["file"].split(".")[-1]
            if lang not in by_lang:
                by_lang[lang] = []
            by_lang[lang].append(failure)
        
        # Print results by language
        for lang, bugs in sorted(by_lang.items()):
            print(f"\n📄 {lang.upper()} ({len(bugs)} bugs detected):")
            for bug in bugs:
                print(f"   Line {bug['line_number']}: {bug['bug_type']} → {bug['message']}")
        
        print("\n" + "=" * 70)
        print(f"TOTAL: {len(failures)} bugs detected across all languages")
        print("=" * 70)
        
        # Validate we detected bugs in all languages
        assert "java" in by_lang, "No Java bugs detected!"
        assert "js" in by_lang, "No JavaScript bugs detected!"
        assert "ts" in by_lang, "No TypeScript bugs detected!"
        
        print("\n✅ Multi-language detection WORKING!")
        print(f"   ✓ Java: {len(by_lang['java'])} bugs")
        print(f"   ✓ JavaScript: {len(by_lang['js'])} bugs")
        print(f"   ✓ TypeScript: {len(by_lang['ts'])} bugs")

if __name__ == "__main__":
    test_multi_language_detection()
