"""
Prometheus-Bench-v1: Code Optimization Benchmark
Focus: Algorithmic complexity, naive vs. optimized solutions, and functional verification.

This benchmark contains 50 Python coding problems designed to test an agent's
ability to identify and resolve algorithmic inefficiencies.
"""

import time
import json
import pytest
import multiprocessing
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict

@dataclass
class CodeProblem:
    """A single coding problem in the benchmark"""
    id: str
    name: str
    description: str
    category: str  # "sorting", "searching", "graph", "dynamic_programming", "string", "math"
    naive_code: str
    optimized_code: str
    test_suite: str
    complexity_naive: str
    complexity_optimized: str

class PrometheusBenchV1:
    """
    Prometheus-Bench-v1 Dataset and Runner
    """
    def __init__(self):
        self.problems: List[CodeProblem] = []
        self._load_initial_problems()

    def _load_initial_problems(self):
        """Load the first set of 50 problems"""
        
        # 1. Bubble Sort vs Quick Sort
        self.problems.append(CodeProblem(
            id="PB-001",
            name="Sorting Integers",
            category="sorting",
            description="Sort a list of integers in ascending order.",
            naive_code="""
def sort_list(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data
""",
            optimized_code="""
def sort_list(data):
    return sorted(data)
""",
            test_suite="""
def test_sort_list():
    assert sort_list([5, 2, 9, 1, 5, 6]) == [1, 2, 5, 5, 6, 9]
    assert sort_list([]) == []
    assert sort_list([1]) == [1]
    import random
    large_list = [random.randint(0, 1000) for _ in range(100)]
    assert sort_list(large_list[:]) == sorted(large_list)
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n log n)"
        ))

        # 2. Linear Search vs Binary Search
        self.problems.append(CodeProblem(
            id="PB-002",
            name="Searching in Sorted List",
            category="searching",
            description="Find the index of a target element in a sorted list. Return -1 if not found.",
            naive_code="""
def find_element(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
""",
            optimized_code="""
def find_element(arr, target):
    import bisect
    i = bisect.bisect_left(arr, target)
    if i != len(arr) and arr[i] == target:
        return i
    return -1
""",
            test_suite="""
def test_find_element():
    arr = [1, 2, 4, 4, 5, 7, 9]
    assert find_element(arr, 4) in [2, 3]
    assert find_element(arr, 1) == 0
    assert find_element(arr, 9) == 6
    assert find_element(arr, 10) == -1
    assert find_element([], 5) == -1
""",
            complexity_naive="O(n)",
            complexity_optimized="O(log n)"
        ))

        # 3. Fibonacci Recursive vs DP
        self.problems.append(CodeProblem(
            id="PB-003",
            name="Nth Fibonacci Number",
            category="dynamic_programming",
            description="Calculate the nth Fibonacci number.",
            naive_code="""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
            optimized_code="""
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
""",
            test_suite="""
def test_fibonacci():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(10) == 55
    assert fibonacci(20) == 6765
""",
            complexity_naive="O(2^n)",
            complexity_optimized="O(n)"
        ))

        # 4. Finding Duplicates in List
        self.problems.append(CodeProblem(
            id="PB-004",
            name="Find Duplicates",
            category="searching",
            description="Find all duplicate elements in a list.",
            naive_code="""
def find_duplicates(items):
    dups = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j] and items[i] not in dups:
                dups.append(items[i])
    return dups
""",
            optimized_code="""
def find_duplicates(items):
    seen = set()
    dups = set()
    for item in items:
        if item in seen:
            dups.add(item)
        seen.add(item)
    return list(dups)
""",
            test_suite="""
def test_find_duplicates():
    assert sorted(find_duplicates([1, 2, 3, 1, 2, 4])) == [1, 2]
    assert find_duplicates([1, 2, 3]) == []
    assert find_duplicates([]) == []
    assert find_duplicates([1, 1, 1, 1]) == [1]
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 5. Matrix Exponentiation (Naive Power) vs Optimized
        self.problems.append(CodeProblem(
            id="PB-005",
            name="Power Function",
            category="math",
            description="Calculate x raised to the power n (x^n).",
            naive_code="""
def power(x, n):
    if n < 0:
        return 1 / power(x, -n)
    res = 1
    for _ in range(n):
        res *= x
    return res
""",
            optimized_code="""
def power(x, n):
    if n < 0:
        x = 1 / x
        n = -n
    res = 1
    while n > 0:
        if n % 2 == 1:
            res *= x
        x *= x
        n //= 2
    return res
""",
            test_suite="""
def test_power():
    assert power(2, 10) == 1024
    assert power(3, 3) == 27
    assert abs(power(2, -2) - 0.25) < 1e-9
    assert power(5, 0) == 1
""",
            complexity_naive="O(n)",
            complexity_optimized="O(log n)"
        ))

        # 6. Sum of Squares (Naive Loop) vs Formula
        self.problems.append(CodeProblem(
            id="PB-006",
            name="Sum of First N Squares",
            category="math",
            description="Calculate the sum of squares of first n natural numbers.",
            naive_code="""
def sum_squares(n):
    total = 0
    for i in range(1, n + 1):
        total += i * i
    return total
""",
            optimized_code="""
def sum_squares(n):
    return n * (n + 1) * (2 * n + 1) // 6
""",
            test_suite="""
def test_sum_squares():
    assert sum_squares(1) == 1
    assert sum_squares(3) == 14 # 1+4+9
    assert sum_squares(10) == 385
""",
            complexity_naive="O(n)",
            complexity_optimized="O(1)"
        ))

        # 7. Longest Common Substring (Naive) vs DP
        self.problems.append(CodeProblem(
            id="PB-007",
            name="Longest Common Substring Length",
            category="dynamic_programming",
            description="Find the length of the longest common substring between two strings.",
            naive_code="""
def lcs_length(s1, s2):
    max_len = 0
    for i in range(len(s1)):
        for j in range(len(s2)):
            k = 0
            while i + k < len(s1) and j + k < len(s2) and s1[i+k] == s2[j+k]:
                k += 1
                max_len = max(max_len, k)
    return max_len
""",
            optimized_code="""
def lcs_length(s1, s2):
    n, m = len(s1), len(s2)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    max_len = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                max_len = max(max_len, dp[i][j])
    return max_len
""",
            test_suite="""
def test_lcs_length():
    assert lcs_length("abcde", "abfde") == 2 # "ab" or "de"
    assert lcs_length("photograph", "tomography") == 6 # "ograph"
    assert lcs_length("apple", "pear") == 1
    assert lcs_length("", "abc") == 0
""",
            complexity_naive="O(n * m * min(n,m))",
            complexity_optimized="O(n * m)"
        ))

        # 8. Prime Sieve (Naive check) vs Sieve
        self.problems.append(CodeProblem(
            id="PB-008",
            name="Primes up to N",
            category="math",
            description="Return a list of all prime numbers up to n.",
            naive_code="""
def get_primes(n):
    primes = []
    for i in range(2, n + 1):
        is_prime = True
        for j in range(2, i):
            if i % j == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(i)
    return primes
""",
            optimized_code="""
def get_primes(n):
    if n < 2: return []
    sieve = [True] * (n + 1)
    for p in range(2, int(n**0.5) + 1):
        if sieve[p]:
            for i in range(p * p, n + 1, p):
                sieve[i] = False
    return [p for p in range(2, n + 1) if sieve[p]]
""",
            test_suite="""
def test_get_primes():
    assert get_primes(10) == [2, 3, 5, 7]
    assert get_primes(2) == [2]
    assert get_primes(1) == []
    assert len(get_primes(100)) == 25
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n log log n)"
        ))

        # 9. Anagram Check (Naive sorting) vs Hash Map
        self.problems.append(CodeProblem(
            id="PB-009",
            name="Anagram Check",
            category="string",
            description="Check if two strings are anagrams of each other.",
            naive_code="""
def are_anagrams(s1, s2):
    return sorted(s1.lower().replace(" ", "")) == sorted(s2.lower().replace(" ", ""))
""",
            optimized_code="""
def are_anagrams(s1, s2):
    s1, s2 = s1.lower().replace(" ", ""), s2.lower().replace(" ", "")
    if len(s1) != len(s2): return False
    counts = {}
    for char in s1:
        counts[char] = counts.get(char, 0) + 1
    for char in s2:
        if char not in counts: return False
        counts[char] -= 1
        if counts[char] < 0: return False
    return True
""",
            test_suite="""
def test_are_anagrams():
    assert are_anagrams("Listen", "Silent") is True
    assert are_anagrams("Hello", "World") is False
    assert are_anagrams("astronomer", "moon starer") is True
    assert are_anagrams("a", "b") is False
""",
            complexity_naive="O(n log n)",
            complexity_optimized="O(n)"
        ))

        # 10. List Intersection (Naive) vs Set
        self.problems.append(CodeProblem(
            id="PB-010",
            name="List Intersection",
            category="searching",
            description="Find the intersection of two lists.",
            naive_code="""
def intersect(l1, l2):
    res = []
    for x in l1:
        if x in l2 and x not in res:
            res.append(x)
    return res
""",
            optimized_code="""
def intersect(l1, l2):
    return list(set(l1) & set(l2))
""",
            test_suite="""
def test_intersect():
    assert sorted(intersect([1, 2, 3], [2, 3, 4])) == [2, 3]
    assert intersect([1, 1, 1], [1, 1]) == [1]
    assert intersect([], [1, 2]) == []
    assert intersect([1, 2], [3, 4]) == []
""",
            complexity_naive="O(n * m)",
            complexity_optimized="O(n + m)"
        ))

        # 11. BFS for Shortest Path in Unweighted Graph (Naive DFS) vs BFS
        self.problems.append(CodeProblem(
            id="PB-011",
            name="Shortest Path Unweighted",
            category="graph",
            description="Find the shortest path length between start and end nodes in an unweighted graph.",
            naive_code="""
def shortest_path(adj, start, end):
    def dfs(curr, target, visited, depth):
        if curr == target: return depth
        visited.add(curr)
        min_depth = float('inf')
        for neighbor in adj.get(curr, []):
            if neighbor not in visited:
                d = dfs(neighbor, target, visited.copy(), depth + 1)
                min_depth = min(min_depth, d)
        return min_depth
    
    res = dfs(start, end, set(), 0)
    return res if res != float('inf') else -1
""",
            optimized_code="""
from collections import deque
def shortest_path(adj, start, end):
    if start == end: return 0
    queue = deque([(start, 0)])
    visited = {start}
    while queue:
        curr, dist = queue.popleft()
        if curr == end: return dist
        for neighbor in adj.get(curr, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return -1
""",
            test_suite="""
def test_shortest_path():
    adj = {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2]}
    assert shortest_path(adj, 0, 3) == 2
    assert shortest_path(adj, 0, 0) == 0
    assert shortest_path({0: [1]}, 0, 2) == -1
""",
            complexity_naive="O(2^V)",
            complexity_optimized="O(V + E)"
        ))

        # 12. Matrix Transpose (Naive) vs List Comprehension
        self.problems.append(CodeProblem(
            id="PB-012",
            name="Matrix Transpose",
            category="math",
            description="Transpose an m x n matrix.",
            naive_code="""
def transpose(matrix):
    if not matrix: return []
    m, n = len(matrix), len(matrix[0])
    res = [[0] * m for _ in range(n)]
    for i in range(m):
        for j in range(n):
            res[j][i] = matrix[i][j]
    return res
""",
            optimized_code="""
def transpose(matrix):
    return [list(row) for row in zip(*matrix)]
""",
            test_suite="""
def test_transpose():
    m = [[1, 2], [3, 4], [5, 6]]
    expected = [[1, 3, 5], [2, 4, 6]]
    assert transpose(m) == expected
    assert transpose([]) == []
""",
            complexity_naive="O(m * n)",
            complexity_optimized="O(m * n)"
        ))

        # 13. Two Sum (Naive) vs Hash Map
        self.problems.append(CodeProblem(
            id="PB-013",
            name="Two Sum",
            category="searching",
            description="Find indices of two numbers that add up to a target.",
            naive_code="""
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return None
""",
            optimized_code="""
def two_sum(nums, target):
    lookup = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in lookup:
            return [lookup[diff], i]
        lookup[num] = i
    return None
""",
            test_suite="""
def test_two_sum():
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]
    assert two_sum([3, 2, 4], 6) == [1, 2]
    assert two_sum([3, 3], 6) == [0, 1]
    assert two_sum([1, 2], 5) is None
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 14. Maximum Subarray (Naive) vs Kadane's
        self.problems.append(CodeProblem(
            id="PB-014",
            name="Maximum Subarray Sum",
            category="dynamic_programming",
            description="Find the sum of the contiguous subarray with the largest sum.",
            naive_code="""
def max_subarray(nums):
    max_sum = float('-inf')
    for i in range(len(nums)):
        for j in range(i, len(nums)):
            curr_sum = sum(nums[i:j+1])
            max_sum = max(max_sum, curr_sum)
    return max_sum
""",
            optimized_code="""
def max_subarray(nums):
    if not nums: return 0
    max_so_far = current_max = nums[0]
    for x in nums[1:]:
        current_max = max(x, current_max + x)
        max_so_far = max(max_so_far, current_max)
    return max_so_far
""",
            test_suite="""
def test_max_subarray():
    assert max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert max_subarray([1]) == 1
    assert max_subarray([5, 4, -1, 7, 8]) == 23
""",
            complexity_naive="O(n^3)",
            complexity_optimized="O(n)"
        ))

        # 15. Valid Parentheses (Naive) vs Stack
        self.problems.append(CodeProblem(
            id="PB-015",
            name="Valid Parentheses",
            category="string",
            description="Check if the input string has valid matching parentheses.",
            naive_code="""
def is_valid(s):
    while "()" in s or "[]" in s or "{}" in s:
        s = s.replace("()", "").replace("[]", "").replace("{}", "")
    return s == ""
""",
            optimized_code="""
def is_valid(s):
    stack = []
    mapping = {")": "(", "}": "{", "]": "["}
    for char in s:
        if char in mapping:
            top_element = stack.pop() if stack else '#'
            if mapping[char] != top_element:
                return False
        else:
            stack.append(char)
    return not stack
""",
            test_suite="""
def test_is_valid():
    assert is_valid("()") is True
    assert is_valid("()[]{}") is True
    assert is_valid("(]") is False
    assert is_valid("([)]") is False
    assert is_valid("{[]}") is True
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 16. Power Set (Naive Recursive) vs Bit Manipulation
        self.problems.append(CodeProblem(
            id="PB-016",
            name="Power Set",
            category="math",
            description="Generate all subsets of a given set.",
            naive_code="""
def power_set(s):
    res = [[]]
    for elem in s:
        res.extend([subset + [elem] for subset in res])
    return res
""",
            optimized_code="""
def power_set(s):
    n = len(s)
    res = []
    for i in range(1 << n):
        subset = [s[j] for j in range(n) if (i & (1 << j))]
        res.append(subset)
    return res
""",
            test_suite="""
def test_power_set():
    res = power_set([1, 2])
    assert sorted([sorted(x) for x in res]) == [[], [1], [1, 2], [2]]
    assert len(power_set([1, 2, 3])) == 8
""",
            complexity_naive="O(2^n)",
            complexity_optimized="O(2^n)"
        ))

        # 17. String Compression (Naive) vs Two Pointers
        self.problems.append(CodeProblem(
            id="PB-017",
            name="String Compression",
            category="string",
            description="Compress string using counts of repeated characters (e.g., 'aabcccccaaa' -> 'a2b1c5a3').",
            naive_code="""
def compress(s):
    if not s: return ""
    res = ""
    i = 0
    while i < len(s):
        char = s[i]
        count = 0
        while i < len(s) and s[i] == char:
            count += 1
            i += 1
        res += char + str(count)
    return res if len(res) < len(s) else s
""",
            optimized_code="""
def compress(s):
    if not s: return ""
    res = []
    count = 0
    for i in range(len(s)):
        count += 1
        if i + 1 >= len(s) or s[i] != s[i+1]:
            res.append(s[i])
            res.append(str(count))
            count = 0
    result = "".join(res)
    return result if len(result) < len(s) else s
""",
            test_suite="""
def test_compress():
    assert compress("aabcccccaaa") == "a2b1c5a3"
    assert compress("abcd") == "abcd"
    assert compress("") == ""
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 18. Rotate Array (Naive) vs Slicing
        self.problems.append(CodeProblem(
            id="PB-018",
            name="Rotate Array",
            category="sorting",
            description="Rotate an array k steps to the right.",
            naive_code="""
def rotate(nums, k):
    n = len(nums)
    if n == 0: return nums
    k %= n
    for _ in range(k):
        last = nums.pop()
        nums.insert(0, last)
    return nums
""",
            optimized_code="""
def rotate(nums, k):
    n = len(nums)
    if n == 0: return nums
    k %= n
    nums[:] = nums[n-k:] + nums[:n-k]
    return nums
""",
            test_suite="""
def test_rotate():
    assert rotate([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]
    assert rotate([1, 2], 3) == [2, 1]
    assert rotate([], 5) == []
""",
            complexity_naive="O(n * k)",
            complexity_optimized="O(n)"
        ))

        # 19. Intersection of Two Linked Lists (Naive) vs Two Pointers
        self.problems.append(CodeProblem(
            id="PB-019",
            name="Intersection Point",
            category="searching",
            description="Find the intersection point of two lists represented as lists.",
            naive_code="""
def find_intersection(l1, l2):
    for x in l1:
        if x in l2:
            return x
    return None
""",
            optimized_code="""
def find_intersection(l1, l2):
    s2 = set(l2)
    for x in l1:
        if x in s2:
            return x
    return None
""",
            test_suite="""
def test_find_intersection():
    assert find_intersection([1, 2, 3, 4], [5, 6, 3, 4]) == 3
    assert find_intersection([1, 2], [3, 4]) is None
""",
            complexity_naive="O(n * m)",
            complexity_optimized="O(n + m)"
        ))

        # 20. Count Set Bits (Naive) vs Brian Kernighan's
        self.problems.append(CodeProblem(
            id="PB-020",
            name="Count Set Bits",
            category="math",
            description="Count the number of 1s in the binary representation of a number.",
            naive_code="""
def count_bits(n):
    return bin(n).count('1')
""",
            optimized_code="""
def count_bits(n):
    count = 0
    while n:
        n &= (n - 1)
        count += 1
    return count
""",
            test_suite="""
def test_count_bits():
    assert count_bits(7) == 3 # 111
    assert count_bits(8) == 1 # 1000
    assert count_bits(0) == 0
""",
            complexity_naive="O(log n)",
            complexity_optimized="O(number of set bits)"
        ))

        # 21. Dijkstra's Algorithm (Naive Array) vs Heap
        self.problems.append(CodeProblem(
            id="PB-021",
            name="Dijkstra Shortest Path",
            category="graph",
            description="Find shortest path in a weighted graph from source.",
            naive_code="""
def dijkstra(graph, start):
    dist = {v: float('inf') for v in graph}
    dist[start] = 0
    visited = set()
    while len(visited) < len(graph):
        min_v = None
        for v in graph:
            if v not in visited:
                if min_v is None or dist[v] < dist[min_v]:
                    min_v = v
        if dist[min_v] == float('inf'): break
        visited.add(min_v)
        for neighbor, weight in graph[min_v].items():
            dist[neighbor] = min(dist[neighbor], dist[min_v] + weight)
    return dist
""",
            optimized_code="""
import heapq
def dijkstra(graph, start):
    dist = {v: float('inf') for v in graph}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v, weight in graph[u].items():
            if dist[u] + weight < dist[v]:
                dist[v] = dist[u] + weight
                heapq.heappush(pq, (dist[v], v))
    return dist
""",
            test_suite="""
def test_dijkstra():
    graph = {0: {1: 4, 2: 1}, 1: {3: 1}, 2: {1: 2, 3: 5}, 3: {}}
    assert dijkstra(graph, 0) == {0: 0, 1: 3, 2: 1, 3: 4}
""",
            complexity_naive="O(V^2)",
            complexity_optimized="O(E log V)"
        ))

        # 22. Trie Search (Naive Set) vs Trie
        self.problems.append(CodeProblem(
            id="PB-022",
            name="Prefix Search",
            category="searching",
            description="Search for words starting with a prefix.",
            naive_code="""
def prefix_search(words, prefix):
    return [w for w in words if w.startswith(prefix)]
""",
            optimized_code="""
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()
    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True

def prefix_search(words, prefix):
    trie = Trie()
    for w in words: trie.insert(w)
    node = trie.root
    for char in prefix:
        if char not in node.children: return []
        node = node.children[char]
    
    res = []
    def dfs(n, current_prefix):
        if n.is_end: res.append(current_prefix)
        for char, child in n.children.items():
            dfs(child, current_prefix + char)
    
    dfs(node, prefix)
    return res
""",
            test_suite="""
def test_prefix_search():
    words = ["apple", "app", "apricot", "banana"]
    assert sorted(prefix_search(words, "app")) == ["app", "apple"]
    assert prefix_search(words, "cat") == []
""",
            complexity_naive="O(N * L)",
            complexity_optimized="O(L + K) where K is result size"
        ))

        # 23. Merge Intervals (Naive) vs Sorting + Single Pass
        self.problems.append(CodeProblem(
            id="PB-023",
            name="Merge Overlapping Intervals",
            category="sorting",
            description="Merge overlapping intervals in a list.",
            naive_code="""
def merge_intervals(intervals):
    if not intervals: return []
    intervals.sort()
    i = 0
    while i < len(intervals) - 1:
        if intervals[i][1] >= intervals[i+1][0]:
            intervals[i] = [intervals[i][0], max(intervals[i][1], intervals[i+1][1])]
            intervals.pop(i+1)
        else:
            i += 1
    return intervals
""",
            optimized_code="""
def merge_intervals(intervals):
    if not intervals: return []
    intervals.sort()
    merged = [intervals[0]]
    for current in intervals[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            last[1] = max(last[1], current[1])
        else:
            merged.append(current)
    return merged
""",
            test_suite="""
def test_merge_intervals():
    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]
    assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]
    assert merge_intervals([]) == []
""",
            complexity_naive="O(n^2) due to pop",
            complexity_optimized="O(n log n)"
        ))

        # 24. Finding First Non-Repeating Character (Naive) vs Hash Map
        self.problems.append(CodeProblem(
            id="PB-024",
            name="First Non-Repeating Character",
            category="string",
            description="Find the first character in a string that does not repeat.",
            naive_code="""
def first_unique(s):
    for i in range(len(s)):
        if s.count(s[i]) == 1:
            return s[i]
    return None
""",
            optimized_code="""
def first_unique(s):
    counts = {}
    for char in s:
        counts[char] = counts.get(char, 0) + 1
    for char in s:
        if counts[char] == 1:
            return char
    return None
""",
            test_suite="""
def test_first_unique():
    assert first_unique("leetcode") == "l"
    assert first_unique("loveleetcode") == "v"
    assert first_unique("aabb") is None
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 25. Palindrome Partitioning (Naive Recursive) vs DP
        self.problems.append(CodeProblem(
            id="PB-025",
            name="Palindrome Partitioning Count",
            category="dynamic_programming",
            description="Minimum cuts needed for palindrome partitioning.",
            naive_code="""
def min_cuts(s):
    if s == s[::-1]: return 0
    res = len(s) - 1
    for i in range(1, len(s)):
        if s[:i] == s[:i][::-1]:
            res = min(res, 1 + min_cuts(s[i:]))
    return res
""",
            optimized_code="""
def min_cuts(s):
    n = len(s)
    if n <= 1: return 0
    dp = list(range(n))
    for i in range(n):
        # Odd length palindromes
        l, r = i, i
        while l >= 0 and r < n and s[l] == s[r]:
            dp[r] = min(dp[r], (dp[l-1] + 1) if l > 0 else 0)
            l -= 1; r += 1
        # Even length palindromes
        l, r = i, i + 1
        while l >= 0 and r < n and s[l] == s[r]:
            dp[r] = min(dp[r], (dp[l-1] + 1) if l > 0 else 0)
            l -= 1; r += 1
    return dp[n-1]
""",
            test_suite="""
def test_min_cuts():
    assert min_cuts("aab") == 1 # "aa", "b"
    assert min_cuts("ab") == 1
    assert min_cuts("aba") == 0
    assert min_cuts("abcde") == 4
""",
            complexity_naive="O(2^n)",
            complexity_optimized="O(n^2)"
        ))

        # 26. Reverse Linked List (Naive) vs In-place
        self.problems.append(CodeProblem(
            id="PB-026",
            name="Reverse List Content",
            category="sorting",
            description="Reverse the elements of a list.",
            naive_code="""
def reverse_list(data):
    res = []
    for i in range(len(data)-1, -1, -1):
        res.append(data[i])
    return res
""",
            optimized_code="""
def reverse_list(data):
    data.reverse()
    return data
""",
            test_suite="""
def test_reverse_list():
    assert reverse_list([1, 2, 3]) == [3, 2, 1]
    assert reverse_list([]) == []
""",
            complexity_naive="O(n)",
            complexity_optimized="O(n) but in-place"
        ))

        # 27. Binary Search for Square Root (Naive) vs Binary Search
        self.problems.append(CodeProblem(
            id="PB-027",
            name="Integer Square Root",
            category="math",
            description="Find the floor of square root of x.",
            naive_code="""
def my_sqrt(x):
    if x < 2: return x
    for i in range(x + 1):
        if i * i > x:
            return i - 1
""",
            optimized_code="""
def my_sqrt(x):
    if x < 2: return x
    l, r = 1, x // 2
    while l <= r:
        m = (l + r) // 2
        if m * m == x: return m
        if m * m < x: l = m + 1
        else: r = m - 1
    return r
""",
            test_suite="""
def test_my_sqrt():
    assert my_sqrt(4) == 2
    assert my_sqrt(8) == 2
    assert my_sqrt(0) == 0
    assert my_sqrt(1) == 1
""",
            complexity_naive="O(sqrt(x))",
            complexity_optimized="O(log x)"
        ))

        # 28. Valid BST Check (Naive Recursive) vs Range-based
        self.problems.append(CodeProblem(
            id="PB-028",
            name="Valid Binary Search Tree",
            category="graph",
            description="Check if a binary tree (list format) is a valid BST.",
            naive_code="""
def is_valid_bst(tree, index=0):
    if index >= len(tree) or tree[index] is None: return True
    val = tree[index]
    left = 2 * index + 1
    right = 2 * index + 2
    
    # Naive only checks immediate children
    if left < len(tree) and tree[left] is not None and tree[left] >= val: return False
    if right < len(tree) and tree[right] is not None and tree[right] <= val: return False
    
    return is_valid_bst(tree, left) and is_valid_bst(tree, right)
""",
            optimized_code="""
def is_valid_bst(tree):
    def validate(index, low=float('-inf'), high=float('inf')):
        if index >= len(tree) or tree[index] is None: return True
        val = tree[index]
        if val <= low or val >= high: return False
        return validate(2*index+1, low, val) and validate(2*index+2, val, high)
    return validate(0)
""",
            test_suite="""
def test_is_valid_bst():
    assert is_valid_bst([2, 1, 3]) is True
    assert is_valid_bst([5, 1, 4, None, None, 3, 6]) is False
""",
            complexity_naive="O(n) but incorrect logic",
            complexity_optimized="O(n)"
        ))

        # 29. Counting Paths in Grid (Naive Recursive) vs DP
        self.problems.append(CodeProblem(
            id="PB-029",
            name="Unique Paths in Grid",
            category="dynamic_programming",
            description="Count unique paths from top-left to bottom-right in an m x n grid.",
            naive_code="""
def count_paths(m, n):
    if m == 1 or n == 1: return 1
    return count_paths(m - 1, n) + count_paths(m, n - 1)
""",
            optimized_code="""
def count_paths(m, n):
    dp = [1] * n
    for _ in range(1, m):
        for j in range(1, n):
            dp[j] += dp[j - 1]
    return dp[n - 1]
""",
            test_suite="""
def test_count_paths():
    assert count_paths(3, 7) == 28
    assert count_paths(3, 2) == 3
    assert count_paths(1, 1) == 1
""",
            complexity_naive="O(2^(m+n))",
            complexity_optimized="O(m * n)"
        ))

        # 30. Find Longest Palindromic Substring (Naive) vs Manacher's or DP
        self.problems.append(CodeProblem(
            id="PB-030",
            name="Longest Palindrome Substring",
            category="string",
            description="Find the longest palindromic substring.",
            naive_code="""
def longest_palindrome(s):
    max_p = ""
    for i in range(len(s)):
        for j in range(i, len(s)):
            sub = s[i:j+1]
            if sub == sub[::-1] and len(sub) > len(max_p):
                max_p = sub
    return max_p
""",
            optimized_code="""
def longest_palindrome(s):
    if not s: return ""
    start = end = 0
    def expand(l, r):
        while l >= 0 and r < len(s) and s[l] == s[r]:
            l -= 1; r += 1
        return l + 1, r - 1
    for i in range(len(s)):
        l1, r1 = expand(i, i)
        l2, r2 = expand(i, i + 1)
        if r1 - l1 > end - start: start, end = l1, r1
        if r2 - l2 > end - start: start, end = l2, r2
    return s[start:end+1]
""",
            test_suite="""
def test_longest_palindrome():
    assert longest_palindrome("babad") in ["bab", "aba"]
    assert longest_palindrome("cbbd") == "bb"
    assert longest_palindrome("a") == "a"
""",
            complexity_naive="O(n^3)",
            complexity_optimized="O(n^2)"
        ))

        # 31. Course Schedule (Naive Recursive) vs Kahn's or DFS
        self.problems.append(CodeProblem(
            id="PB-031",
            name="Course Schedule Check",
            category="graph",
            description="Determine if it's possible to finish all courses (cycle detection).",
            naive_code="""
def can_finish(numCourses, prerequisites):
    adj = {i: [] for i in range(numCourses)}
    for u, v in prerequisites: adj[u].append(v)
    def has_cycle(u, visited):
        if u in visited: return True
        visited.add(u)
        for v in adj[u]:
            if has_cycle(v, visited.copy()): return True
        return False
    for i in range(numCourses):
        if has_cycle(i, set()): return False
    return True
""",
            optimized_code="""
def can_finish(numCourses, prerequisites):
    adj = [[] for _ in range(numCourses)]
    for u, v in prerequisites: adj[u].append(v)
    visit = [0] * numCourses # 0=unvisited, 1=visiting, 2=visited
    def has_cycle(u):
        if visit[u] == 1: return True
        if visit[u] == 2: return False
        visit[u] = 1
        for v in adj[u]:
            if has_cycle(v): return True
        visit[u] = 2
        return False
    for i in range(numCourses):
        if has_cycle(i): return False
    return True
""",
            test_suite="""
def test_can_finish():
    assert can_finish(2, [[1, 0]]) is True
    assert can_finish(2, [[1, 0], [0, 1]]) is False
    assert can_finish(4, [[1, 0], [2, 1], [3, 2]]) is True
""",
            complexity_naive="O(V^V)",
            complexity_optimized="O(V + E)"
        ))

        # 32. Longest Substring Without Repeating Characters (Naive) vs Sliding Window
        self.problems.append(CodeProblem(
            id="PB-032",
            name="Longest Unique Substring Length",
            category="string",
            description="Find the length of the longest substring without repeating characters.",
            naive_code="""
def length_of_longest_substring(s):
    res = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            sub = s[i:j+1]
            if len(set(sub)) == len(sub):
                res = max(res, len(sub))
    return res
""",
            optimized_code="""
def length_of_longest_substring(s):
    seen = {}
    res = start = 0
    for i, char in enumerate(s):
        if char in seen and start <= seen[char]:
            start = seen[char] + 1
        else:
            res = max(res, i - start + 1)
        seen[char] = i
    return res
""",
            test_suite="""
def test_length_of_longest_substring():
    assert length_of_longest_substring("abcabcbb") == 3
    assert length_of_longest_substring("bbbbb") == 1
    assert length_of_longest_substring("pwwkew") == 3
    assert length_of_longest_substring("") == 0
""",
            complexity_naive="O(n^3)",
            complexity_optimized="O(n)"
        ))

        # 33. House Robber (Naive Recursive) vs DP
        self.problems.append(CodeProblem(
            id="PB-033",
            name="Max House Robbery",
            category="dynamic_programming",
            description="Max amount you can rob without robbing adjacent houses.",
            naive_code="""
def rob(nums):
    def helper(i):
        if i >= len(nums): return 0
        return max(nums[i] + helper(i+2), helper(i+1))
    return helper(0)
""",
            optimized_code="""
def rob(nums):
    prev, curr = 0, 0
    for x in nums:
        prev, curr = curr, max(prev + x, curr)
    return curr
""",
            test_suite="""
def test_rob():
    assert rob([1, 2, 3, 1]) == 4
    assert rob([2, 7, 9, 3, 1]) == 12
    assert rob([]) == 0
""",
            complexity_naive="O(2^n)",
            complexity_optimized="O(n)"
        ))

        # 34. Find All Anagrams (Naive) vs Sliding Window
        self.problems.append(CodeProblem(
            id="PB-034",
            name="All Anagram Indices",
            category="string",
            description="Find all start indices of p's anagrams in s.",
            naive_code="""
def find_anagrams(s, p):
    res = []
    p_sorted = sorted(p)
    for i in range(len(s) - len(p) + 1):
        if sorted(s[i:i+len(p)]) == p_sorted:
            res.append(i)
    return res
""",
            optimized_code="""
from collections import Counter
def find_anagrams(s, p):
    ns, np = len(s), len(p)
    if ns < np: return []
    p_count = Counter(p)
    s_count = Counter(s[:np-1])
    res = []
    for i in range(np - 1, ns):
        s_count[s[i]] += 1
        if s_count == p_count: res.append(i - np + 1)
        s_count[s[i-np+1]] -= 1
        if s_count[s[i-np+1]] == 0: del s_count[s[i-np+1]]
    return res
""",
            test_suite="""
def test_find_anagrams():
    assert find_anagrams("cbaebabacd", "abc") == [0, 6]
    assert find_anagrams("abab", "ab") == [0, 1, 2]
    assert find_anagrams("a", "abc") == []
""",
            complexity_naive="O(ns * np log np)",
            complexity_optimized="O(ns)"
        ))

        # 35. Word Break (Naive Recursive) vs DP
        self.problems.append(CodeProblem(
            id="PB-035",
            name="Word Break Check",
            category="dynamic_programming",
            description="Check if a string can be segmented into space-separated dictionary words.",
            naive_code="""
def word_break(s, wordDict):
    if not s: return True
    for word in wordDict:
        if s.startswith(word):
            if word_break(s[len(word):], wordDict): return True
    return False
""",
            optimized_code="""
def word_break(s, wordDict):
    word_set = set(wordDict)
    dp = [False] * (len(s) + 1)
    dp[0] = True
    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in word_set:
                dp[i] = True
                break
    return dp[len(s)]
""",
            test_suite="""
def test_word_break():
    assert word_break("leetcode", ["leet", "code"]) is True
    assert word_break("applepenapple", ["apple", "pen"]) is True
    assert word_break("catsandog", ["cats", "dog", "sand", "and", "cat"]) is False
""",
            complexity_naive="O(2^n)",
            complexity_optimized="O(n^2)"
        ))

        # 36. Single Number (Naive) vs XOR
        self.problems.append(CodeProblem(
            id="PB-036",
            name="Find Single Number",
            category="math",
            description="Every element appears twice except for one. Find that single one.",
            naive_code="""
def single_number(nums):
    for x in nums:
        if nums.count(x) == 1:
            return x
""",
            optimized_code="""
def single_number(nums):
    res = 0
    for x in nums: res ^= x
    return res
""",
            test_suite="""
def test_single_number():
    assert single_number([2, 2, 1]) == 1
    assert single_number([4, 1, 2, 1, 2]) == 4
    assert single_number([1]) == 1
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 37. Move Zeroes (Naive) vs In-place
        self.problems.append(CodeProblem(
            id="PB-037",
            name="Move Zeroes to End",
            category="sorting",
            description="Move all 0's to the end while maintaining the relative order of non-zero elements.",
            naive_code="""
def move_zeroes(nums):
    n = len(nums)
    i = 0
    zeros = 0
    while i < n - zeros:
        if nums[i] == 0:
            nums.pop(i)
            nums.append(0)
            zeros += 1
        else:
            i += 1
    return nums
""",
            optimized_code="""
def move_zeroes(nums):
    last_non_zero = 0
    for i in range(len(nums)):
        if nums[i] != 0:
            nums[last_non_zero], nums[i] = nums[i], nums[last_non_zero]
            last_non_zero += 1
    return nums
""",
            test_suite="""
def test_move_zeroes():
    assert move_zeroes([0, 1, 0, 3, 12]) == [1, 3, 12, 0, 0]
    assert move_zeroes([0]) == [0]
    assert move_zeroes([1, 2, 3]) == [1, 2, 3]
""",
            complexity_naive="O(n^2) due to pop/append",
            complexity_optimized="O(n)"
        ))

        # 38. Best Time to Buy and Sell Stock (Naive) vs One Pass
        self.problems.append(CodeProblem(
            id="PB-038",
            name="Max Stock Profit",
            category="dynamic_programming",
            description="Find max profit from one transaction.",
            naive_code="""
def max_profit(prices):
    max_p = 0
    for i in range(len(prices)):
        for j in range(i + 1, len(prices)):
            max_p = max(max_p, prices[j] - prices[i])
    return max_p
""",
            optimized_code="""
def max_profit(prices):
    min_price = float('inf')
    max_p = 0
    for price in prices:
        min_price = min(min_price, price)
        max_p = max(max_p, price - min_price)
    return max_p
""",
            test_suite="""
def test_max_profit():
    assert max_profit([7, 1, 5, 3, 6, 4]) == 5
    assert max_profit([7, 6, 4, 3, 1]) == 0
    assert max_profit([]) == 0
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 39. Rotate Image (Naive) vs Transpose + Reverse
        self.problems.append(CodeProblem(
            id="PB-039",
            name="Rotate Image 90 Degrees",
            category="math",
            description="Rotate an n x n 2D matrix 90 degrees clockwise in-place.",
            naive_code="""
def rotate_image(matrix):
    import copy
    n = len(matrix)
    old = copy.deepcopy(matrix)
    for i in range(n):
        for j in range(n):
            matrix[j][n-1-i] = old[i][j]
    return matrix
""",
            optimized_code="""
def rotate_image(matrix):
    n = len(matrix)
    # Transpose
    for i in range(n):
        for j in range(i, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    # Reverse rows
    for i in range(n):
        matrix[i].reverse()
    return matrix
""",
            test_suite="""
def test_rotate_image():
    m = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    expected = [[7, 4, 1], [8, 5, 2], [9, 6, 3]]
    assert rotate_image(m) == expected
""",
            complexity_naive="O(n^2) with O(n^2) space",
            complexity_optimized="O(n^2) with O(1) space"
        ))

        # 40. Product of Array Except Self (Naive) vs Prefix/Suffix
        self.problems.append(CodeProblem(
            id="PB-040",
            name="Array Product Except Self",
            category="math",
            description="Return an array such that res[i] is product of all elements except nums[i]. Do it without division.",
            naive_code="""
def product_except_self(nums):
    res = []
    for i in range(len(nums)):
        p = 1
        for j in range(len(nums)):
            if i != j: p *= nums[j]
        res.append(p)
    return res
""",
            optimized_code="""
def product_except_self(nums):
    n = len(nums)
    res = [1] * n
    # Prefix
    for i in range(1, n):
        res[i] = res[i-1] * nums[i-1]
    # Suffix
    suffix = 1
    for i in range(n-1, -1, -1):
        res[i] *= suffix
        suffix *= nums[i]
    return res
""",
            test_suite="""
def test_product_except_self():
    assert product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]
    assert product_except_self([-1, 1, 0, -3, 3]) == [0, 0, 9, 0, 0]
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 41. 3Sum (Naive) vs Sorting + Two Pointers
        self.problems.append(CodeProblem(
            id="PB-041",
            name="3Sum to Zero",
            category="searching",
            description="Find all unique triplets in the array which gives the sum of zero.",
            naive_code="""
def three_sum(nums):
    res = set()
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                if nums[i] + nums[j] + nums[k] == 0:
                    res.add(tuple(sorted((nums[i], nums[j], nums[k]))))
    return [list(x) for x in res]
""",
            optimized_code="""
def three_sum(nums):
    res = []
    nums.sort()
    for i in range(len(nums)-2):
        if i > 0 and nums[i] == nums[i-1]: continue
        l, r = i+1, len(nums)-1
        while l < r:
            s = nums[i] + nums[l] + nums[r]
            if s < 0: l += 1
            elif s > 0: r -= 1
            else:
                res.append([nums[i], nums[l], nums[r]])
                while l < r and nums[l] == nums[l+1]: l += 1
                while l < r and nums[r] == nums[r-1]: r -= 1
                l += 1; r -= 1
    return res
""",
            test_suite="""
def test_three_sum():
    res = three_sum([-1, 0, 1, 2, -1, -4])
    assert sorted([sorted(x) for x in res]) == [[-1, -1, 2], [-1, 0, 1]]
    assert three_sum([0, 1, 1]) == []
    assert three_sum([0, 0, 0]) == [[0, 0, 0]]
""",
            complexity_naive="O(n^3)",
            complexity_optimized="O(n^2)"
        ))

        # 42. Lowest Common Ancestor (Naive Recursive) vs LCA
        self.problems.append(CodeProblem(
            id="PB-042",
            name="Lowest Common Ancestor Binary Tree",
            category="graph",
            description="Find the lowest common ancestor (LCA) of two nodes in a binary tree (list format).",
            naive_code="""
def find_lca(tree, p, q):
    def get_path(idx, target, path):
        if idx >= len(tree) or tree[idx] is None: return False
        path.append(idx)
        if tree[idx] == target: return True
        if get_path(2*idx+1, target, path) or get_path(2*idx+2, target, path): return True
        path.pop()
        return False
    
    path_p, path_q = [], []
    get_path(0, p, path_p)
    get_path(0, q, path_q)
    
    lca_idx = 0
    for i in range(min(len(path_p), len(path_q))):
        if path_p[i] == path_q[i]: lca_idx = path_p[i]
        else: break
    return tree[lca_idx]
""",
            optimized_code="""
def find_lca(tree, p, q, idx=0):
    if idx >= len(tree) or tree[idx] is None: return None
    if tree[idx] == p or tree[idx] == q: return tree[idx]
    
    left = find_lca(tree, p, q, 2*idx+1)
    right = find_lca(tree, p, q, 2*idx+2)
    
    if left and right: return tree[idx]
    return left if left else right
""",
            test_suite="""
def test_find_lca():
    tree = [3, 5, 1, 6, 2, 0, 8, None, None, 7, 4]
    assert find_lca(tree, 5, 1) == 3
    assert find_lca(tree, 5, 4) == 5
""",
            complexity_naive="O(n) but multiple passes",
            complexity_optimized="O(n) single pass"
        ))

        # 43. Longest Increasing Subsequence (Naive Recursive) vs DP
        self.problems.append(CodeProblem(
            id="PB-043",
            name="Longest Increasing Subsequence Length",
            category="dynamic_programming",
            description="Find the length of the longest strictly increasing subsequence.",
            naive_code="""
def length_of_lis(nums):
    def helper(i, prev):
        if i == len(nums): return 0
        taken = 0
        if nums[i] > prev:
            taken = 1 + helper(i+1, nums[i])
        not_taken = helper(i+1, prev)
        return max(taken, not_taken)
    return helper(0, float('-inf'))
""",
            optimized_code="""
def length_of_lis(nums):
    if not nums: return 0
    dp = [1] * len(nums)
    for i in range(len(nums)):
        for j in range(i):
            if nums[i] > nums[j]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
""",
            test_suite="""
def test_length_of_lis():
    assert length_of_lis([10, 9, 2, 5, 3, 7, 101, 18]) == 4
    assert length_of_lis([0, 1, 0, 3, 2, 3]) == 4
    assert length_of_lis([7, 7, 7]) == 1
""",
            complexity_naive="O(2^n)",
            complexity_optimized="O(n^2) or O(n log n)"
        ))

        # 44. Jump Game (Naive Recursive) vs Greedy
        self.problems.append(CodeProblem(
            id="PB-044",
            name="Can Jump to End",
            category="dynamic_programming",
            description="Check if you can reach the last index starting from index 0.",
            naive_code="""
def can_jump(nums):
    def helper(pos):
        if pos >= len(nums) - 1: return True
        furthest = min(pos + nums[pos], len(nums) - 1)
        for i in range(pos + 1, furthest + 1):
            if helper(i): return True
        return False
    return helper(0)
""",
            optimized_code="""
def can_jump(nums):
    goal = len(nums) - 1
    for i in range(len(nums)-1, -1, -1):
        if i + nums[i] >= goal: goal = i
    return goal == 0
""",
            test_suite="""
def test_can_jump():
    assert can_jump([2, 3, 1, 1, 4]) is True
    assert can_jump([3, 2, 1, 0, 4]) is False
""",
            complexity_naive="O(2^n)",
            complexity_optimized="O(n)"
        ))

        # 45. Find Minimum in Rotated Sorted Array (Naive) vs Binary Search
        self.problems.append(CodeProblem(
            id="PB-045",
            name="Min in Rotated Array",
            category="searching",
            description="Find the minimum element in a rotated sorted array.",
            naive_code="""
def find_min(nums):
    return min(nums)
""",
            optimized_code="""
def find_min(nums):
    l, r = 0, len(nums) - 1
    while l < r:
        m = (l + r) // 2
        if nums[m] > nums[r]: l = m + 1
        else: r = m
    return nums[l]
""",
            test_suite="""
def test_find_min():
    assert find_min([3, 4, 5, 1, 2]) == 1
    assert find_min([4, 5, 6, 7, 0, 1, 2]) == 0
    assert find_min([11, 13, 15, 17]) == 11
""",
            complexity_naive="O(n)",
            complexity_optimized="O(log n)"
        ))

        # 46. Word Search (Naive Recursive) vs Backtracking
        self.problems.append(CodeProblem(
            id="PB-046",
            name="Word Search on Grid",
            category="graph",
            description="Check if a word exists in a grid of characters.",
            naive_code="""
def exist(board, word):
    def dfs(r, c, k, visited):
        if k == len(word): return True
        if r < 0 or r >= len(board) or c < 0 or c >= len(board[0]) or \
           (r, c) in visited or board[r][c] != word[k]: return False
        visited.add((r, c))
        res = dfs(r+1, c, k+1, visited.copy()) or \
              dfs(r-1, c, k+1, visited.copy()) or \
              dfs(r, c+1, k+1, visited.copy()) or \
              dfs(r, c-1, k+1, visited.copy())
        return res
    
    for i in range(len(board)):
        for j in range(len(board[0])):
            if exist(board, word): # Error: Recursive call to self
                pass
    return False # Implementation incomplete but for optimization task
""",
            optimized_code="""
def exist(board, word):
    rows, cols = len(board), len(board[0])
    def backtrack(r, c, k):
        if k == len(word): return True
        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != word[k]:
            return False
        temp = board[r][c]
        board[r][c] = "#" # Mark visited
        for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
            if backtrack(r + dr, c + dc, k + 1): return True
        board[r][c] = temp # Backtrack
        return False
    for i in range(rows):
        for j in range(cols):
            if backtrack(i, j, 0): return True
    return False
""",
            test_suite="""
def test_exist():
    board = [["A","B","C","E"],["S","F","C","S"],["A","D","E","E"]]
    assert exist(board, "ABCCED") is True
    assert exist(board, "SEE") is True
    assert exist(board, "ABCB") is False
""",
            complexity_naive="O(N * 4^L) with many copies",
            complexity_optimized="O(N * 3^L)"
        ))

        # 47. Coin Change (Naive Recursive) vs DP
        self.problems.append(CodeProblem(
            id="PB-047",
            name="Minimum Coins for Amount",
            category="dynamic_programming",
            description="Find fewest number of coins to make up an amount.",
            naive_code="""
def coin_change(coins, amount):
    if amount == 0: return 0
    if amount < 0: return -1
    res = float('inf')
    for coin in coins:
        sub = coin_change(coins, amount - coin)
        if sub != -1: res = min(res, 1 + sub)
    return res if res != float('inf') else -1
""",
            optimized_code="""
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for a in range(1, amount + 1):
        for c in coins:
            if a - c >= 0:
                dp[a] = min(dp[a], 1 + dp[a - c])
    return dp[amount] if dp[amount] != float('inf') else -1
""",
            test_suite="""
def test_coin_change():
    assert coin_change([1, 2, 5], 11) == 3
    assert coin_change([2], 3) == -1
    assert coin_change([1], 0) == 0
""",
            complexity_naive="O(S^n)",
            complexity_optimized="O(S * n)"
        ))

        # 48. Missing Number (Naive) vs Math/XOR
        self.problems.append(CodeProblem(
            id="PB-048",
            name="Find Missing Number",
            category="math",
            description="Find the one missing number from [0, n] in the array.",
            naive_code="""
def missing_number(nums):
    n = len(nums)
    for i in range(n + 1):
        if i not in nums:
            return i
""",
            optimized_code="""
def missing_number(nums):
    n = len(nums)
    return n * (n + 1) // 2 - sum(nums)
""",
            test_suite="""
def test_missing_number():
    assert missing_number([3, 0, 1]) == 2
    assert missing_number([0, 1]) == 2
    assert missing_number([9, 6, 4, 2, 3, 5, 7, 0, 1]) == 8
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 49. Container With Most Water (Naive) vs Two Pointers
        self.problems.append(CodeProblem(
            id="PB-049",
            name="Max Water Container",
            category="searching",
            description="Find two lines that together with x-axis forms a container that contains the most water.",
            naive_code="""
def max_area(height):
    max_a = 0
    for i in range(len(height)):
        for j in range(i + 1, len(height)):
            area = min(height[i], height[j]) * (j - i)
            max_a = max(max_a, area)
    return max_a
""",
            optimized_code="""
def max_area(height):
    l, r = 0, len(height) - 1
    max_a = 0
    while l < r:
        area = min(height[l], height[r]) * (r - l)
        max_a = max(max_a, area)
        if height[l] < height[r]: l += 1
        else: r -= 1
    return max_a
""",
            test_suite="""
def test_max_area():
    assert max_area([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49
    assert max_area([1, 1]) == 1
""",
            complexity_naive="O(n^2)",
            complexity_optimized="O(n)"
        ))

        # 50. Happy Number (Naive) vs Floyd's Cycle Finding
        self.problems.append(CodeProblem(
            id="PB-050",
            name="Happy Number Check",
            category="math",
            description="Determine if a number is happy (eventually reaches 1 by summing squares of digits).",
            naive_code="""
def is_happy(n):
    seen = []
    while n != 1:
        n = sum(int(d)**2 for d in str(n))
        if n in seen: return False
        seen.append(n)
    return True
""",
            optimized_code="""
def is_happy(n):
    def get_next(num):
        total = 0
        while num > 0:
            num, digit = divmod(num, 10)
            total += digit ** 2
        return total
    slow = n
    fast = get_next(n)
    while fast != 1 and slow != fast:
        slow = get_next(slow)
        fast = get_next(get_next(fast))
    return fast == 1
""",
            test_suite="""
def test_is_happy():
    assert is_happy(19) is True
    assert is_happy(2) is False
""",
            complexity_naive="O(log n) space for seen",
            complexity_optimized="O(log n) with O(1) space"
        ))


    def save_to_json(self, filepath: str):
        """Save the benchmark problems to a JSON file"""
        data = [asdict(p) for p in self.problems]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def run_tests(self, problem_id: str, use_optimized: bool = False) -> bool:
        """Run tests for a specific problem using either naive or optimized code"""
        problem = next((p for p in self.problems if p.id == problem_id), None)
        if not problem:
            return False
        
        code = problem.optimized_code if use_optimized else problem.naive_code
        full_code = code + "\n" + problem.test_suite
        
        # In a real environment, we'd use a safer execution method
        try:
            exec_globals = {}
            exec(full_code, exec_globals)
            # Find all functions starting with 'test_'
            test_functions = [f for name, f in exec_globals.items() if name.startswith('test_')]
            for test_func in test_functions:
                test_func()
            return True
        except Exception as e:
            print(f"Test failed for {problem_id}: {e}")
            return False

if __name__ == "__main__":
    bench = PrometheusBenchV1()
    print(f"Loaded {len(bench.problems)} problems.")
    
    # Save to benchmarks/prometheus_bench_v1.json
    bench.save_to_json("benchmarks/prometheus_bench_v1.json")
    print("Saved to benchmarks/prometheus_bench_v1.json")
    
    # Verify first problem
    success = bench.run_tests("PB-001", use_optimized=True)
    print(f"PB-001 Optimized Test: {'Pass' if success else 'Fail'}")
    
    success_naive = bench.run_tests("PB-001", use_optimized=False)
    print(f"PB-001 Naive Test: {'Pass' if success_naive else 'Fail'}")
