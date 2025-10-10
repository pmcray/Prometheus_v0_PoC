#!/usr/bin/env python3
"""
USACO Bronze-Level Test Problems

Collection of competitive programming problems for benchmarking IOI Bronze system.
Based on actual USACO Bronze difficulty level.
"""

# Problem 1: Count Even Numbers (Easy)
PROBLEM_1 = {
    'name': 'Count Even Numbers',
    'difficulty': 'Easy',
    'text': """
Count Even Numbers

You are given an array of N integers. Count how many of them are even.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers (1 ≤ each ≤ 10^9)

Output:
- A single integer: the count of even numbers
""",
    'examples': [
        {'input': '5\n2 4 6 8 10', 'output': '5'},
        {'input': '3\n1 3 5', 'output': '0'},
        {'input': '4\n1 2 3 4', 'output': '2'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_array', 'count_if']
}

# Problem 2: Find Maximum (Easy)
PROBLEM_2 = {
    'name': 'Find Maximum',
    'difficulty': 'Easy',
    'text': """
Find Maximum

Given N integers, find the maximum value.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers (1 ≤ each ≤ 10^9)

Output:
- A single integer: the maximum value
""",
    'examples': [
        {'input': '5\n3 7 2 9 1', 'output': '9'},
        {'input': '3\n100 200 50', 'output': '200'},
        {'input': '1\n42', 'output': '42'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_array', 'find_max']
}

# Problem 3: Sum of Array (Easy)
PROBLEM_3 = {
    'name': 'Sum of Array',
    'difficulty': 'Easy',
    'text': """
Sum of Array

Calculate the sum of all elements in an array.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers (1 ≤ each ≤ 10^9)

Output:
- A single integer: the sum of all elements
""",
    'examples': [
        {'input': '5\n1 2 3 4 5', 'output': '15'},
        {'input': '3\n10 20 30', 'output': '60'},
        {'input': '1\n100', 'output': '100'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_array']
}

# Problem 4: Count Occurrences (Medium)
PROBLEM_4 = {
    'name': 'Count Occurrences',
    'difficulty': 'Medium',
    'text': """
Count Occurrences

Given an array of N integers and a target value X, count how many times X appears.

Input:
- First line: N and X (1 ≤ N ≤ 1000, 1 ≤ X ≤ 10^9)
- Second line: N space-separated integers

Output:
- A single integer: count of X in the array
""",
    'examples': [
        {'input': '5 3\n1 3 3 7 3', 'output': '3'},
        {'input': '4 10\n5 10 15 20', 'output': '1'},
        {'input': '3 5\n1 2 3', 'output': '0'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_array', 'count_if']
}

# Problem 5: Reverse Array (Medium)
PROBLEM_5 = {
    'name': 'Reverse Array',
    'difficulty': 'Medium',
    'text': """
Reverse Array

Print the elements of an array in reverse order.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- N space-separated integers in reverse order
""",
    'examples': [
        {'input': '5\n1 2 3 4 5', 'output': '5 4 3 2 1'},
        {'input': '3\n10 20 30', 'output': '30 20 10'},
        {'input': '1\n42', 'output': '42'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_array']
}

# Problem 6: Check Sorted (Medium)
PROBLEM_6 = {
    'name': 'Check Sorted',
    'difficulty': 'Medium',
    'text': """
Check Sorted

Determine if an array is sorted in non-decreasing order.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- "YES" if sorted, "NO" otherwise
""",
    'examples': [
        {'input': '5\n1 2 3 4 5', 'output': 'YES'},
        {'input': '4\n1 3 2 4', 'output': 'NO'},
        {'input': '3\n5 5 5', 'output': 'YES'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_array']
}

# Problem 7: Two Sum Exists (Medium-Hard)
PROBLEM_7 = {
    'name': 'Two Sum Exists',
    'difficulty': 'Medium-Hard',
    'text': """
Two Sum Exists

Given an array and a target sum S, determine if there exist two elements that sum to S.

Input:
- First line: N and S (1 ≤ N ≤ 1000, 1 ≤ S ≤ 10^9)
- Second line: N space-separated integers

Output:
- "YES" if such a pair exists, "NO" otherwise
""",
    'examples': [
        {'input': '5 10\n1 2 3 4 5', 'output': 'YES'},  # 4+6 doesn't work, but we have other pairs
        {'input': '4 100\n10 20 30 40', 'output': 'NO'},
        {'input': '3 6\n1 2 3', 'output': 'YES'},  # 3+3
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_set', 'use_array']
}

# Problem 8: Frequency Map (Medium)
PROBLEM_8 = {
    'name': 'Most Frequent Element',
    'difficulty': 'Medium',
    'text': """
Most Frequent Element

Find the element that appears most frequently. If there's a tie, output the smallest value.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers (1 ≤ each ≤ 10^9)

Output:
- A single integer: the most frequent element
""",
    'examples': [
        {'input': '7\n1 2 2 3 3 3 4', 'output': '3'},
        {'input': '5\n5 5 5 5 5', 'output': '5'},
        {'input': '4\n1 2 1 2', 'output': '1'},  # Tie, output smaller
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_frequency_map', 'find_max']
}

# Problem 9: Binary Search (Hard)
PROBLEM_9 = {
    'name': 'Binary Search',
    'difficulty': 'Hard',
    'text': """
Binary Search

Given a sorted array and a target value, find its index (0-indexed).
If not found, output -1.

Input:
- First line: N and X (1 ≤ N ≤ 1000, 1 ≤ X ≤ 10^9)
- Second line: N space-separated integers in non-decreasing order

Output:
- Index of X (0-indexed), or -1 if not found
""",
    'examples': [
        {'input': '5 3\n1 2 3 4 5', 'output': '2'},
        {'input': '4 10\n5 10 15 20', 'output': '1'},
        {'input': '3 7\n1 2 3', 'output': '-1'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['binary_search', 'use_array']
}

# Problem 10: Palindrome Check (Medium)
PROBLEM_10 = {
    'name': 'Palindrome String',
    'difficulty': 'Medium',
    'text': """
Palindrome String

Check if a given string is a palindrome (reads the same forwards and backwards).

Input:
- A single line: a string S (1 ≤ length ≤ 1000)

Output:
- "YES" if palindrome, "NO" otherwise
""",
    'examples': [
        {'input': 'racecar', 'output': 'YES'},
        {'input': 'hello', 'output': 'NO'},
        {'input': 'a', 'output': 'YES'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['string_is_palindrome']
}

# All problems
ALL_PROBLEMS = [
    PROBLEM_1,
    PROBLEM_2,
    PROBLEM_3,
    PROBLEM_4,
    PROBLEM_5,
    PROBLEM_6,
    PROBLEM_7,
    PROBLEM_8,
    PROBLEM_9,
    PROBLEM_10,
]


def get_problem_by_difficulty(difficulty):
    """Get all problems of a specific difficulty"""
    return [p for p in ALL_PROBLEMS if p['difficulty'] == difficulty]


def get_easy_problems():
    """Get easy problems (good for testing)"""
    return get_problem_by_difficulty('Easy')


def get_medium_problems():
    """Get medium problems"""
    return [p for p in ALL_PROBLEMS if 'Medium' in p['difficulty']]


def get_hard_problems():
    """Get hard problems"""
    return get_problem_by_difficulty('Hard')


if __name__ == "__main__":
    print("USACO Bronze Test Problems")
    print("=" * 70)
    print(f"\nTotal problems: {len(ALL_PROBLEMS)}")
    print(f"Easy: {len(get_easy_problems())}")
    print(f"Medium: {len(get_medium_problems())}")
    print(f"Hard: {len(get_hard_problems())}")

    print("\n" + "=" * 70)
    print("Problem List:")
    print("=" * 70)

    for i, problem in enumerate(ALL_PROBLEMS, 1):
        print(f"\n{i}. {problem['name']} ({problem['difficulty']})")
        print(f"   Algorithms: {', '.join(problem['solution_algorithms'])}")
        print(f"   Examples: {len(problem['examples'])}")
