import pytest
from prometheus.ast_analyzer import ASTComplexityAnalyzer

def test_no_loops():
    code = """
def my_func(a, b):
    return a + b
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["max_loop_depth"] == 0

def test_single_for_loop():
    code = """
def my_func(n):
    for i in range(n):
        print(i)
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["max_loop_depth"] == 1

def test_nested_for_loops():
    code = """
def my_func(n):
    for i in range(n):
        for j in range(n):
            print(i, j)
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["max_loop_depth"] == 2

def test_deeper_nested_loops():
    code = """
def my_func(n):
    for i in range(n):
        for j in range(n):
            for k in range(n):
                print(i, j, k)
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["max_loop_depth"] == 3

def test_sequential_loops():
    code = """
def my_func(n):
    for i in range(n):
        print(i)
    for j in range(n):
        print(j)
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["max_loop_depth"] == 1

def test_no_recursion():
    code = """
def factorial(n):
    res = 1
    for i in range(1, n + 1):
        res *= i
    return res
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert not metrics["recursion_detected"]

def test_simple_recursion():
    code = """
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["recursion_detected"]

def test_multiple_functions():
    code = """
def func_a(n):
    for i in range(n):
        for j in range(n):
            print(i, j)

def func_b(n):
    for i in range(n):
        print(i)
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["max_loop_depth"] == 2
    assert not metrics["recursion_detected"]

def test_multiple_functions_with_recursion():
    code = """
def func_a(n):
    for i in range(n):
        for j in range(n):
            print(i, j)

def fib(n):
    if n <= 1:
        return n
    else:
        return fib(n-1) + fib(n-2)
"""
    analyzer = ASTComplexityAnalyzer(code)
    metrics = analyzer.analyze()
    assert metrics["max_loop_depth"] == 2
    assert metrics["recursion_detected"]
