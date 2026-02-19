"""Debug INDENTATION fix."""

lines = [
    "import math",
    "",
    "def calculate_area(radius): # SYNTAX: missing colon",
    "    pi = 3.14",
    "    area = pi * radius ^ 2",
    "    return area",
    "",
    "def greet(name):  # INDENTATION: missing indent on next line",
    "print(\"Hello \" + name)",  # Line 8, index 8, this one needs indent
]

index = 8
original = lines[index]
print(f"Current line {index+1}: {repr(original)}")
print(f"First char: {repr(original[0])}")
space_chars = (' ', '\t')
print(f"Is space or tab: {original[0] in space_chars}")

if index > 0:
    prev_line = lines[index - 1]
    print(f"Previous line: {repr(prev_line)}")
    prev_stripped = prev_line.strip()
    print(f"Previous stripped: {repr(prev_stripped)}")
    print(f"Previous ends with colon: {prev_stripped.endswith(':')}")
    
    current_indent = len(original) - len(original.lstrip())
    prev_indent = len(prev_line) - len(prev_line.lstrip())
    expected_indent = prev_indent + 4
    
    print(f"Current indent: {current_indent}")
    print(f"Previous indent: {prev_indent}")
    print(f"Expected indent: {expected_indent}")
    print(f"Line starts with space/tab: {original and original[0] in space_chars}")
    
    if original and original[0] not in space_chars:
        print("-> Should indent this line!")


