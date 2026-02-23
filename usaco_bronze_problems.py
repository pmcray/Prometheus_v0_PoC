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

# Problem 11: Sort Array (Easy)
PROBLEM_11 = {
    'name': 'Sort Array',
    'difficulty': 'Easy',
    'text': """
Sort Array

Sort N integers in ascending order.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- N space-separated integers in ascending order
""",
    'examples': [
        {'input': '5\n5 2 8 1 9', 'output': '1 2 5 8 9'},
        {'input': '3\n3 3 3', 'output': '3 3 3'},
        {'input': '4\n10 5 20 15', 'output': '5 10 15 20'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['sort_ascending', 'use_array']
}

# Problem 12: Count Unique (Medium)
PROBLEM_12 = {
    'name': 'Count Unique Elements',
    'difficulty': 'Medium',
    'text': """
Count Unique Elements

Count how many distinct elements are in an array.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- A single integer: count of unique elements
""",
    'examples': [
        {'input': '7\n1 2 2 3 3 3 4', 'output': '4'},
        {'input': '5\n5 5 5 5 5', 'output': '1'},
        {'input': '4\n1 2 3 4', 'output': '4'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_set', 'use_array']
}

# Problem 13: Range Sum (Easy)
PROBLEM_13 = {
    'name': 'Range Sum',
    'difficulty': 'Easy',
    'text': """
Range Sum

Calculate the sum of integers from L to R (inclusive).

Input:
- Two integers L and R (1 ≤ L ≤ R ≤ 10^6)

Output:
- A single integer: sum from L to R
""",
    'examples': [
        {'input': '1 5', 'output': '15'},  # 1+2+3+4+5
        {'input': '10 10', 'output': '10'},
        {'input': '1 100', 'output': '5050'},
    ],
    'constraints': {'n_max': 1000000, 'time_limit_ms': 2000},
    'solution_algorithms': []
}

# Problem 14: Prefix Sum Query (Medium-Hard)
PROBLEM_14 = {
    'name': 'Prefix Sum Query',
    'difficulty': 'Medium-Hard',
    'text': """
Prefix Sum Query

Given an array and Q queries, answer range sum queries.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers
- Third line: Q (1 ≤ Q ≤ 1000)
- Next Q lines: L R (0-indexed, sum from index L to R inclusive)

Output:
- Q lines: sum for each query
""",
    'examples': [
        {'input': '5\n1 2 3 4 5\n3\n0 2\n1 4\n0 4', 'output': '6\n14\n15'},
        {'input': '3\n10 20 30\n2\n0 0\n0 2', 'output': '10\n60'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_prefix_sum', 'use_array']
}

# Problem 15: Min and Max (Easy)
PROBLEM_15 = {
    'name': 'Min and Max',
    'difficulty': 'Easy',
    'text': """
Min and Max

Find both the minimum and maximum values in an array.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- Two integers: min max
""",
    'examples': [
        {'input': '5\n3 7 2 9 1', 'output': '1 9'},
        {'input': '3\n5 5 5', 'output': '5 5'},
        {'input': '4\n10 20 30 40', 'output': '10 40'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['find_min', 'find_max', 'use_array']
}

# Problem 16: GCD (Medium)
PROBLEM_16 = {
    'name': 'Greatest Common Divisor',
    'difficulty': 'Medium',
    'text': """
Greatest Common Divisor

Find the GCD of two integers.

Input:
- Two integers A and B (1 ≤ A, B ≤ 10^9)

Output:
- A single integer: GCD(A, B)
""",
    'examples': [
        {'input': '12 8', 'output': '4'},
        {'input': '7 5', 'output': '1'},
        {'input': '100 50', 'output': '50'},
    ],
    'constraints': {'n_max': 1000000000, 'time_limit_ms': 2000},
    'solution_algorithms': ['math_gcd']
}

# Problem 17: Prime Check (Medium)
PROBLEM_17 = {
    'name': 'Prime Number Check',
    'difficulty': 'Medium',
    'text': """
Prime Number Check

Determine if a number is prime.

Input:
- A single integer N (2 ≤ N ≤ 10^6)

Output:
- "YES" if prime, "NO" otherwise
""",
    'examples': [
        {'input': '7', 'output': 'YES'},
        {'input': '10', 'output': 'NO'},
        {'input': '97', 'output': 'YES'},
    ],
    'constraints': {'n_max': 1000000, 'time_limit_ms': 2000},
    'solution_algorithms': ['math_is_prime']
}

# Problem 18: Fibonacci (Medium)
PROBLEM_18 = {
    'name': 'Nth Fibonacci Number',
    'difficulty': 'Medium',
    'text': """
Nth Fibonacci Number

Calculate the Nth Fibonacci number (F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2)).

Input:
- A single integer N (0 ≤ N ≤ 30)

Output:
- A single integer: F(N)
""",
    'examples': [
        {'input': '5', 'output': '5'},  # 0,1,1,2,3,5
        {'input': '10', 'output': '55'},
        {'input': '0', 'output': '0'},
    ],
    'constraints': {'n_max': 30, 'time_limit_ms': 2000},
    'solution_algorithms': ['dp_fibonacci']
}

# Problem 19: Max Subarray Sum (Hard)
PROBLEM_19 = {
    'name': 'Maximum Subarray Sum',
    'difficulty': 'Hard',
    'text': """
Maximum Subarray Sum

Find the maximum sum of a contiguous subarray.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers (-10^6 ≤ each ≤ 10^6)

Output:
- A single integer: maximum subarray sum
""",
    'examples': [
        {'input': '5\n-2 1 -3 4 -1', 'output': '4'},  # [4]
        {'input': '8\n-2 -3 4 -1 -2 1 5 -3', 'output': '7'},  # [4,-1,-2,1,5]
        {'input': '3\n1 2 3', 'output': '6'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['dp_max_subarray_sum']
}

# Problem 20: Longest Increasing Subsequence (Hard)
PROBLEM_20 = {
    'name': 'Longest Increasing Subsequence',
    'difficulty': 'Hard',
    'text': """
Longest Increasing Subsequence

Find the length of the longest strictly increasing subsequence.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- A single integer: LIS length
""",
    'examples': [
        {'input': '8\n10 9 2 5 3 7 101 18', 'output': '4'},  # [2,3,7,101] or [2,3,7,18]
        {'input': '4\n1 3 6 7', 'output': '4'},
        {'input': '5\n5 4 3 2 1', 'output': '1'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['dp_longest_increasing_subsequence']
}

# Problem 21: Coin Change (Hard)
PROBLEM_21 = {
    'name': 'Coin Change',
    'difficulty': 'Hard',
    'text': """
Coin Change

Find the minimum number of coins needed to make amount N.
Coins available: 1, 5, 10, 25 cents.

Input:
- A single integer N (1 ≤ N ≤ 10000)

Output:
- A single integer: minimum coins needed
""",
    'examples': [
        {'input': '11', 'output': '2'},  # 10+1
        {'input': '30', 'output': '2'},  # 25+5
        {'input': '99', 'output': '9'},  # 3*25 + 2*10 + 4*1
    ],
    'constraints': {'n_max': 10000, 'time_limit_ms': 2000},
    'solution_algorithms': ['dp_coin_change']
}

# Problem 22: String Reverse (Easy)
PROBLEM_22 = {
    'name': 'Reverse String',
    'difficulty': 'Easy',
    'text': """
Reverse String

Reverse a given string.

Input:
- A single line: a string S (1 ≤ length ≤ 1000)

Output:
- The reversed string
""",
    'examples': [
        {'input': 'hello', 'output': 'olleh'},
        {'input': 'a', 'output': 'a'},
        {'input': 'racecar', 'output': 'racecar'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['string_reverse']
}

# Problem 23: Count Vowels (Easy)
PROBLEM_23 = {
    'name': 'Count Vowels',
    'difficulty': 'Easy',
    'text': """
Count Vowels

Count the number of vowels (a, e, i, o, u) in a string (case-insensitive).

Input:
- A single line: a string S (1 ≤ length ≤ 1000)

Output:
- A single integer: count of vowels
""",
    'examples': [
        {'input': 'hello', 'output': '2'},  # e, o
        {'input': 'AEIOU', 'output': '5'},
        {'input': 'xyz', 'output': '1'},  # y
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['count_if']
}

# Problem 24: Cumulative Sum (Easy)
PROBLEM_24 = {
    'name': 'Cumulative Sum',
    'difficulty': 'Easy',
    'text': """
Cumulative Sum

Output the cumulative sum array.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- N space-separated integers: cumulative sums
""",
    'examples': [
        {'input': '5\n1 2 3 4 5', 'output': '1 3 6 10 15'},
        {'input': '3\n10 20 30', 'output': '10 30 60'},
        {'input': '1\n42', 'output': '42'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['cumulative_sum', 'use_array']
}

# Problem 25: Filter Positive (Easy)
PROBLEM_25 = {
    'name': 'Filter Positive Numbers',
    'difficulty': 'Easy',
    'text': """
Filter Positive Numbers

Output only the positive numbers from an array.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers (-10^6 ≤ each ≤ 10^6)

Output:
- Space-separated positive integers (in original order)
- If none, output "NONE"
""",
    'examples': [
        {'input': '5\n-2 3 -1 5 -4', 'output': '3 5'},
        {'input': '3\n-1 -2 -3', 'output': 'NONE'},
        {'input': '4\n1 2 3 4', 'output': '1 2 3 4'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['filter_by', 'use_array']
}

# Problem 26: Median (Medium)
PROBLEM_26 = {
    'name': 'Median Value',
    'difficulty': 'Medium',
    'text': """
Median Value

Find the median of an array (middle value when sorted).
For even length, use the lower middle value.

Input:
- First line: N (1 ≤ N ≤ 1000, N is odd)
- Second line: N space-separated integers

Output:
- A single integer: the median
""",
    'examples': [
        {'input': '5\n3 1 4 1 5', 'output': '3'},  # Sorted: 1,1,3,4,5
        {'input': '3\n10 5 8', 'output': '8'},  # Sorted: 5,8,10
        {'input': '1\n42', 'output': '42'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['sort_ascending', 'use_array']
}

# Problem 27: Mode (Medium)
PROBLEM_27 = {
    'name': 'Mode Value',
    'difficulty': 'Medium',
    'text': """
Mode Value

Find the mode (most frequent value). If tie, output the smallest.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- A single integer: the mode
""",
    'examples': [
        {'input': '7\n1 2 2 3 3 3 4', 'output': '3'},
        {'input': '4\n1 2 1 2', 'output': '1'},  # Tie, output smaller
        {'input': '5\n5 5 5 5 5', 'output': '5'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_frequency_map', 'find_max']
}

# Problem 28: Second Maximum (Medium)
PROBLEM_28 = {
    'name': 'Second Maximum',
    'difficulty': 'Medium',
    'text': """
Second Maximum

Find the second largest value in an array (distinct values).

Input:
- First line: N (2 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- A single integer: second maximum, or -1 if all same
""",
    'examples': [
        {'input': '5\n3 7 2 9 1', 'output': '7'},
        {'input': '3\n5 5 5', 'output': '-1'},
        {'input': '4\n10 20 30 40', 'output': '30'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_set', 'sort_descending']
}

# Problem 29: Remove Duplicates (Medium)
PROBLEM_29 = {
    'name': 'Remove Duplicates',
    'difficulty': 'Medium',
    'text': """
Remove Duplicates

Remove duplicates from an array, keeping first occurrence.

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- Space-separated integers without duplicates (in original order)
""",
    'examples': [
        {'input': '7\n1 2 2 3 3 3 4', 'output': '1 2 3 4'},
        {'input': '5\n5 5 5 5 5', 'output': '5'},
        {'input': '4\n1 2 3 4', 'output': '1 2 3 4'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['use_set', 'use_array']
}

# Problem 30: Partition Even Odd (Medium)
PROBLEM_30 = {
    'name': 'Partition Even and Odd',
    'difficulty': 'Medium',
    'text': """
Partition Even and Odd

Separate even and odd numbers (evens first, then odds).

Input:
- First line: N (1 ≤ N ≤ 1000)
- Second line: N space-separated integers

Output:
- Two lines:
  - Line 1: Space-separated even numbers (in original order)
  - Line 2: Space-separated odd numbers (in original order)
  - If none for a line, output "NONE"
""",
    'examples': [
        {'input': '5\n1 2 3 4 5', 'output': '2 4\n1 3 5'},
        {'input': '3\n2 4 6', 'output': '2 4 6\nNONE'},
        {'input': '2\n1 3', 'output': 'NONE\n1 3'},
    ],
    'constraints': {'n_max': 1000, 'time_limit_ms': 2000},
    'solution_algorithms': ['filter_by', 'use_array']
}

# All problems
ALL_PROBLEMS = [
    PROBLEM_1, PROBLEM_2, PROBLEM_3, PROBLEM_4, PROBLEM_5,
    PROBLEM_6, PROBLEM_7, PROBLEM_8, PROBLEM_9, PROBLEM_10,
    PROBLEM_11, PROBLEM_12, PROBLEM_13, PROBLEM_14, PROBLEM_15,
    PROBLEM_16, PROBLEM_17, PROBLEM_18, PROBLEM_19, PROBLEM_20,
    PROBLEM_21, PROBLEM_22, PROBLEM_23, PROBLEM_24, PROBLEM_25,
    PROBLEM_26, PROBLEM_27, PROBLEM_28, PROBLEM_29, PROBLEM_30,
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
