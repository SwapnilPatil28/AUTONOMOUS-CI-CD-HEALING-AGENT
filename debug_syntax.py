"""Debug the patch applier."""

line = "def calculate_area(radius)  # SYNTAX: missing colon"

# Split on hash
if "#" not in line:
    code_part, comment_part = line.rstrip(), ""
else:
    hash_index = line.index("#")
    code_part = line[:hash_index].rstrip()
    comment_part = line[hash_index:].lstrip()

print(f"Original: {repr(line)}")
print(f"Code part: {repr(code_part)}")
print(f"Comment part: {repr(comment_part)}")
print(f"Code ends with colon: {code_part.endswith(':')}")

import re
has_keyword = re.search(r"\b(if|elif|for|while|def|class|else|try|except|with)\b", code_part)
print(f"Has keyword: {has_keyword}")
