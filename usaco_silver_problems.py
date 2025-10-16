#!/usr/bin/env python3
"""
USACO Silver Level Problems (curated from CSES, Codeforces, USACO)

Topics:
- Sorting & Comparators
- Prefix Sums
- Two Pointers
- Greedy Algorithms
- Binary Search

Expected Phi-3 Performance: 30-50% (6-10/20)
"""

SILVER_PROBLEMS = [
    # ===== EASY SILVER (1-5) =====
    {
        'id': 'silver_01',
        'name': 'Distinct Numbers',
        'difficulty': 'Easy-Silver',
        'topic': 'Sorting',
        'text': """
You are given a list of n integers. Count how many distinct integers are in the list.

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Second line: n integers (1 ≤ each ≤ 10^9)

Output:
- One integer: number of distinct integers

Constraints: O(n log n) time complexity required
""",
        'examples': [
            {'input': '5\n2 3 2 2 3', 'output': '2'},
            {'input': '10\n1 2 3 4 5 6 7 8 9 10', 'output': '10'},
            {'input': '7\n5 5 5 5 5 5 5', 'output': '1'}
        ]
    },

    {
        'id': 'silver_02',
        'name': 'Sum of Two Values',
        'difficulty': 'Easy-Silver',
        'topic': 'Two Pointers',
        'text': """
You are given an array of n integers and a target sum x.
Find two values in the array that sum to x.

Input:
- First line: n (1 ≤ n ≤ 200,000) and x (1 ≤ x ≤ 10^9)
- Second line: n integers (1 ≤ each ≤ 10^9)

Output:
- Two integers: positions (1-indexed) of the two values
- If no solution exists, print "IMPOSSIBLE"
- If multiple solutions exist, print any one

Constraints: O(n log n) or O(n) time complexity required
""",
        'examples': [
            {'input': '4 8\n2 7 5 1', 'output': '2 3'},
            {'input': '5 15\n1 2 3 4 5', 'output': 'IMPOSSIBLE'},
            {'input': '3 10\n5 5 10', 'output': '1 2'}
        ]
    },

    {
        'id': 'silver_03',
        'name': 'Subarray Sums I',
        'difficulty': 'Easy-Silver',
        'topic': 'Prefix Sums',
        'text': """
Given an array of n positive integers and a target sum x,
count the number of subarrays having sum exactly x.

Input:
- First line: n (1 ≤ n ≤ 200,000) and x (1 ≤ x ≤ 10^9)
- Second line: n positive integers (1 ≤ each ≤ 10^9)

Output:
- One integer: number of subarrays with sum x

Constraints: O(n) time complexity required (two pointers)
""",
        'examples': [
            {'input': '5 7\n2 4 1 2 7', 'output': '3'},
            {'input': '4 5\n1 3 2 5', 'output': '2'},
            {'input': '3 10\n1 2 3', 'output': '0'}
        ]
    },

    {
        'id': 'silver_04',
        'name': 'Movie Festival',
        'difficulty': 'Easy-Silver',
        'topic': 'Greedy',
        'text': """
In a movie festival, n movies will be shown. You know the starting and
ending time of each movie. What is the maximum number of movies you can watch?

You can watch a movie if you arrive before or exactly when it starts.
You must leave before or when a movie ends.

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Next n lines: two integers a and b (start and end time, 1 ≤ a < b ≤ 10^9)

Output:
- One integer: maximum number of movies

Constraints: O(n log n) time complexity required (greedy + sorting)
""",
        'examples': [
            {'input': '3\n3 5\n4 9\n5 8', 'output': '2'},
            {'input': '4\n1 3\n2 5\n3 9\n6 8', 'output': '3'},
            {'input': '2\n1 10\n2 3', 'output': '1'}
        ]
    },

    {
        'id': 'silver_05',
        'name': 'Binary Search',
        'difficulty': 'Easy-Silver',
        'topic': 'Binary Search',
        'text': """
Given a sorted array of n integers and m queries, for each query value x,
find if x exists in the array.

Input:
- First line: n (1 ≤ n ≤ 200,000) and m (1 ≤ m ≤ 200,000)
- Second line: n sorted integers (1 ≤ each ≤ 10^9)
- Next m lines: one integer x per line

Output:
- For each query, print "YES" if x exists, "NO" otherwise

Constraints: O((n + m) log n) time complexity required
""",
        'examples': [
            {'input': '5 3\n1 3 5 7 9\n3\n6\n7', 'output': 'YES\nNO\nYES'},
            {'input': '4 2\n2 4 6 8\n1\n4', 'output': 'NO\nYES'},
            {'input': '3 3\n10 20 30\n15\n20\n25', 'output': 'NO\nYES\nNO'}
        ]
    },

    # ===== MEDIUM SILVER (6-15) =====
    {
        'id': 'silver_06',
        'name': 'Maximum Subarray Sum',
        'difficulty': 'Medium-Silver',
        'topic': 'Prefix Sums',
        'text': """
Given an array of n integers, find the maximum sum of a contiguous subarray.

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Second line: n integers (-10^9 ≤ each ≤ 10^9)

Output:
- One integer: maximum subarray sum

Constraints: O(n) time complexity required (Kadane's algorithm)
""",
        'examples': [
            {'input': '8\n-1 3 -2 5 3 -5 2 2', 'output': '9'},
            {'input': '5\n-5 -4 -3 -2 -1', 'output': '-1'},
            {'input': '4\n1 2 3 4', 'output': '10'}
        ]
    },

    {
        'id': 'silver_07',
        'name': 'Sliding Window Maximum',
        'difficulty': 'Medium-Silver',
        'topic': 'Two Pointers',
        'text': """
Given an array of n integers and a window size k, for each window of size k,
find the maximum element.

Input:
- First line: n (1 ≤ n ≤ 200,000) and k (1 ≤ k ≤ n)
- Second line: n integers (1 ≤ each ≤ 10^9)

Output:
- n-k+1 integers: maximum in each window

Constraints: O(n log k) or O(n) time complexity required
""",
        'examples': [
            {'input': '8 3\n2 4 3 5 1 7 2 4', 'output': '4 5 5 7 7 7'},
            {'input': '5 2\n1 3 2 5 4', 'output': '3 3 5 5'},
            {'input': '4 4\n10 5 8 3', 'output': '10'}
        ]
    },

    {
        'id': 'silver_08',
        'name': 'Ferris Wheel',
        'difficulty': 'Medium-Silver',
        'topic': 'Greedy + Two Pointers',
        'text': """
There are n children who want to go on a Ferris wheel. Each gondola can hold
at most x weight and 1 or 2 children. What is the minimum number of gondolas needed?

Input:
- First line: n (1 ≤ n ≤ 200,000) and x (1 ≤ x ≤ 10^9)
- Second line: n integers (weight of each child, 1 ≤ each ≤ x)

Output:
- One integer: minimum number of gondolas

Constraints: O(n log n) time complexity required
""",
        'examples': [
            {'input': '4 10\n7 2 3 9', 'output': '3'},
            {'input': '5 10\n5 5 5 5 5', 'output': '3'},
            {'input': '6 20\n10 15 8 12 5 18', 'output': '4'}
        ]
    },

    {
        'id': 'silver_09',
        'name': 'Subarray Divisibility',
        'difficulty': 'Medium-Silver',
        'topic': 'Prefix Sums + Hashing',
        'text': """
Given an array of n integers, count the number of subarrays whose sum is
divisible by n.

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Second line: n integers (-10^9 ≤ each ≤ 10^9)

Output:
- One integer: number of subarrays with sum divisible by n

Constraints: O(n) time complexity required
Hint: Use prefix sums modulo n and count pairs with same remainder
""",
        'examples': [
            {'input': '5\n3 1 2 7 4', 'output': '1'},
            {'input': '4\n1 2 3 4', 'output': '2'},
            {'input': '3\n3 3 3', 'output': '3'}
        ]
    },

    {
        'id': 'silver_10',
        'name': 'Sum of Three Values',
        'difficulty': 'Medium-Silver',
        'topic': 'Two Pointers + Sorting',
        'text': """
You are given an array of n integers and a target sum x.
Find three distinct values in the array that sum to x.

Input:
- First line: n (1 ≤ n ≤ 5,000) and x (1 ≤ x ≤ 10^9)
- Second line: n integers (1 ≤ each ≤ 10^9)

Output:
- Three integers: positions (1-indexed) of the three values
- If no solution exists, print "IMPOSSIBLE"

Constraints: O(n²) time complexity required
""",
        'examples': [
            {'input': '4 12\n2 7 5 1', 'output': '1 2 4'},
            {'input': '5 20\n1 2 3 4 5', 'output': 'IMPOSSIBLE'},
            {'input': '5 12\n3 4 5 6 7', 'output': '1 2 5'}
        ]
    },

    {
        'id': 'silver_11',
        'name': 'Factory Machines',
        'difficulty': 'Medium-Silver',
        'topic': 'Binary Search on Answer',
        'text': """
A factory has n machines. The i-th machine creates a product in t_i seconds.
Given a target of x products, what is the minimum time to create them?

You can use all machines simultaneously.

Input:
- First line: n (1 ≤ n ≤ 200,000) and x (1 ≤ x ≤ 10^9)
- Second line: n integers t_i (1 ≤ t_i ≤ 10^9)

Output:
- One integer: minimum time in seconds

Constraints: O(n log T) where T is the answer (binary search on time)
""",
        'examples': [
            {'input': '3 7\n3 2 5', 'output': '8'},
            {'input': '2 10\n5 6', 'output': '30'},
            {'input': '4 100\n1 2 3 4', 'output': '34'}
        ]
    },

    {
        'id': 'silver_12',
        'name': 'Apartments',
        'difficulty': 'Medium-Silver',
        'topic': 'Greedy + Two Pointers',
        'text': """
There are n applicants and m apartments. Each applicant has a desired size,
and each apartment has a size. An applicant can accept an apartment if the
size difference is at most k.

What is the maximum number of applicants who can get an apartment?

Input:
- First line: n, m, k (1 ≤ n,m ≤ 200,000, 0 ≤ k ≤ 10^9)
- Second line: n integers (desired apartment sizes)
- Third line: m integers (apartment sizes)

Output:
- One integer: maximum number of matches

Constraints: O((n+m) log(n+m)) time complexity required
""",
        'examples': [
            {'input': '4 3 5\n60 45 80 60\n30 60 75', 'output': '2'},
            {'input': '3 3 0\n10 20 30\n10 20 30', 'output': '3'},
            {'input': '5 4 10\n50 60 70 80 90\n45 65 75 85', 'output': '4'}
        ]
    },

    {
        'id': 'silver_13',
        'name': 'Concert Tickets',
        'difficulty': 'Medium-Silver',
        'topic': 'Binary Search + Multiset',
        'text': """
There are n concert tickets with different prices, and m customers.
Each customer has a maximum price they're willing to pay.

For each customer (in order), find and sell them the ticket with the highest
price that doesn't exceed their maximum. Each ticket can only be sold once.

Input:
- First line: n, m (1 ≤ n,m ≤ 200,000)
- Second line: n integers (ticket prices, 1 ≤ each ≤ 10^9)
- Third line: m integers (customer max prices, 1 ≤ each ≤ 10^9)

Output:
- m integers: price sold to each customer, or -1 if no ticket available

Constraints: O((n+m) log n) time complexity required
""",
        'examples': [
            {'input': '5 3\n5 3 7 8 5\n4 8 3', 'output': '3\n8\n-1'},
            {'input': '4 4\n10 20 30 40\n15 25 35 45', 'output': '10\n20\n30\n40'},
            {'input': '3 3\n5 5 5\n6 6 6', 'output': '5\n5\n5'}
        ]
    },

    {
        'id': 'silver_14',
        'name': 'Restaurant Customers',
        'difficulty': 'Medium-Silver',
        'topic': 'Sorting + Sweep Line',
        'text': """
A restaurant has n customers. Each customer arrives at time a_i and leaves
at time b_i. What is the maximum number of customers in the restaurant at
any point in time?

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Next n lines: two integers a_i, b_i (1 ≤ a_i < b_i ≤ 10^9)

Output:
- One integer: maximum number of customers simultaneously

Constraints: O(n log n) time complexity required (event-based sorting)
""",
        'examples': [
            {'input': '3\n5 8\n2 4\n3 9', 'output': '2'},
            {'input': '4\n1 3\n2 5\n4 7\n6 9', 'output': '2'},
            {'input': '2\n1 10\n5 15', 'output': '2'}
        ]
    },

    {
        'id': 'silver_15',
        'name': 'Tasks and Deadlines',
        'difficulty': 'Medium-Silver',
        'topic': 'Greedy + Sorting',
        'text': """
You have n tasks. Each task takes d_i days to complete and has a deadline x_i.
You complete tasks one after another. If you finish task i at time f_i,
the reward is x_i - f_i (can be negative).

What is the maximum total reward you can get?

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Next n lines: two integers d_i, x_i (1 ≤ d_i, x_i ≤ 10^6)

Output:
- One integer: maximum total reward

Constraints: O(n log n) time complexity required
Hint: Greedy strategy - which tasks should you do first?
""",
        'examples': [
            {'input': '3\n6 10\n8 15\n5 12', 'output': '2'},
            {'input': '4\n1 10\n2 20\n3 30\n4 40', 'output': '80'},
            {'input': '2\n5 5\n5 5', 'output': '-5'}
        ]
    },

    # ===== HARD SILVER (16-20) =====
    {
        'id': 'silver_16',
        'name': 'Subarray Sums II',
        'difficulty': 'Hard-Silver',
        'topic': 'Prefix Sums + Hashing',
        'text': """
Given an array of n integers (positive and negative) and a target sum x,
count the number of subarrays having sum exactly x.

Input:
- First line: n (1 ≤ n ≤ 200,000) and x (-10^9 ≤ x ≤ 10^9)
- Second line: n integers (-10^9 ≤ each ≤ 10^9)

Output:
- One integer: number of subarrays with sum x

Constraints: O(n) time complexity required (prefix sums + hashmap)
""",
        'examples': [
            {'input': '5 7\n2 -1 3 5 -2', 'output': '2'},
            {'input': '4 0\n1 -1 1 -1', 'output': '4'},
            {'input': '5 5\n1 2 3 -1 4', 'output': '2'}
        ]
    },

    {
        'id': 'silver_17',
        'name': 'Subarray Distinct Values',
        'difficulty': 'Hard-Silver',
        'topic': 'Two Pointers + Sliding Window',
        'text': """
Given an array of n integers, count the number of subarrays that have at
most k distinct values.

Input:
- First line: n (1 ≤ n ≤ 200,000) and k (1 ≤ k ≤ n)
- Second line: n integers (1 ≤ each ≤ 10^9)

Output:
- One integer: number of valid subarrays

Constraints: O(n) time complexity required (two pointers)
""",
        'examples': [
            {'input': '5 2\n1 2 3 1 1', 'output': '10'},
            {'input': '4 1\n1 1 1 1', 'output': '10'},
            {'input': '6 3\n1 2 1 2 3 2', 'output': '18'}
        ]
    },

    {
        'id': 'silver_18',
        'name': 'Array Division',
        'difficulty': 'Hard-Silver',
        'topic': 'Binary Search on Answer',
        'text': """
You are given an array of n integers. You want to divide it into k subarrays
(contiguous segments) such that the maximum sum in a subarray is minimized.

Input:
- First line: n (1 ≤ n ≤ 200,000) and k (1 ≤ k ≤ n)
- Second line: n integers (1 ≤ each ≤ 10^9)

Output:
- One integer: minimum possible maximum sum

Constraints: O(n log S) where S is sum of array (binary search on answer)
""",
        'examples': [
            {'input': '5 3\n2 4 7 3 5', 'output': '8'},
            {'input': '4 2\n1 2 3 4', 'output': '6'},
            {'input': '6 3\n5 1 3 2 4 6', 'output': '7'}
        ]
    },

    {
        'id': 'silver_19',
        'name': 'Nearest Smaller Values',
        'difficulty': 'Hard-Silver',
        'topic': 'Stack + Greedy',
        'text': """
Given an array of n integers, for each position, find the nearest position
to the left that has a smaller value.

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Second line: n integers (1 ≤ each ≤ 10^9)

Output:
- n integers: for each position i, the position of nearest smaller value
  to the left, or 0 if no such position exists

Constraints: O(n) time complexity required (monotonic stack)
""",
        'examples': [
            {'input': '8\n2 5 1 4 8 3 2 5', 'output': '0 1 0 3 4 3 3 7'},
            {'input': '5\n1 2 3 4 5', 'output': '0 1 2 3 4'},
            {'input': '5\n5 4 3 2 1', 'output': '0 0 0 0 0'}
        ]
    },

    {
        'id': 'silver_20',
        'name': 'Room Allocation',
        'difficulty': 'Hard-Silver',
        'topic': 'Greedy + Priority Queue',
        'text': """
A hotel has n customers. Each customer arrives at day a_i and leaves at day b_i.
Assign each customer to a room such that the number of rooms is minimized.

Input:
- First line: n (1 ≤ n ≤ 200,000)
- Next n lines: two integers a_i, b_i (1 ≤ a_i ≤ b_i ≤ 10^9)

Output:
- First line: minimum number of rooms k
- Second line: n integers (room assignment for each customer, 1-indexed)

Constraints: O(n log n) time complexity required
""",
        'examples': [
            {'input': '3\n1 2\n2 4\n4 4', 'output': '2\n1 2 1'},
            {'input': '4\n1 5\n2 6\n3 7\n4 8', 'output': '4\n1 2 3 4'},
            {'input': '2\n1 3\n4 6', 'output': '1\n1 1'}
        ]
    }
]

# Statistics
TOTAL_PROBLEMS = len(SILVER_PROBLEMS)
BY_DIFFICULTY = {
    'Easy-Silver': len([p for p in SILVER_PROBLEMS if p['difficulty'] == 'Easy-Silver']),
    'Medium-Silver': len([p for p in SILVER_PROBLEMS if p['difficulty'] == 'Medium-Silver']),
    'Hard-Silver': len([p for p in SILVER_PROBLEMS if p['difficulty'] == 'Hard-Silver'])
}

BY_TOPIC = {}
for problem in SILVER_PROBLEMS:
    topic = problem['topic']
    BY_TOPIC[topic] = BY_TOPIC.get(topic, 0) + 1

if __name__ == "__main__":
    print(f"USACO Silver Problems: {TOTAL_PROBLEMS}")
    print(f"\nBy Difficulty:")
    for diff, count in BY_DIFFICULTY.items():
        print(f"  {diff}: {count}")
    print(f"\nBy Topic:")
    for topic, count in sorted(BY_TOPIC.items()):
        print(f"  {topic}: {count}")
