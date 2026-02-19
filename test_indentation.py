import nonexistingmodule  # LINTING: unused import
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
