#!/usr/bin/env python3
"""
IOI Bronze Primitive Library (v0.75)

50 fundamental algorithms for competitive programming.
Each primitive is a tested, reusable building block.
"""

import heapq
import bisect
from collections import Counter, deque, defaultdict
from typing import List, Tuple, Dict, Set, Callable, Any
import math

class IOIPrimitives:
    """Library of 50 algorithmic primitives for competitive programming"""

    # ========================================================================
    # DATA STRUCTURES (10 primitives)
    # ========================================================================

    @staticmethod
    def use_array(n: int, value=0) -> List:
        """Initialize array of size n"""
        return [value] * n

    @staticmethod
    def use_2d_array(rows: int, cols: int, value=0) -> List[List]:
        """Initialize 2D array"""
        return [[value for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def use_dict() -> Dict:
        """Initialize dictionary"""
        return {}

    @staticmethod
    def use_set() -> Set:
        """Initialize set"""
        return set()

    @staticmethod
    def use_heap() -> List:
        """Initialize min-heap (use heapq operations)"""
        return []

    @staticmethod
    def use_queue() -> deque:
        """Initialize queue (FIFO)"""
        return deque()

    @staticmethod
    def use_stack() -> List:
        """Initialize stack (LIFO)"""
        return []

    @staticmethod
    def use_frequency_map(arr: List) -> Dict:
        """Count frequencies of elements"""
        return Counter(arr)

    @staticmethod
    def use_prefix_sum(arr: List[int]) -> List[int]:
        """Compute prefix sum array"""
        if not arr:
            return []
        prefix = [0] * (len(arr) + 1)
        for i in range(len(arr)):
            prefix[i + 1] = prefix[i] + arr[i]
        return prefix

    @staticmethod
    def use_defaultdict(default_factory) -> defaultdict:
        """Initialize defaultdict"""
        return defaultdict(default_factory)

    # ========================================================================
    # SEARCHING & SORTING (5 primitives)
    # ========================================================================

    @staticmethod
    def linear_search(arr: List, target) -> int:
        """Find index of target (-1 if not found)"""
        try:
            return arr.index(target)
        except ValueError:
            return -1

    @staticmethod
    def binary_search(arr: List, target) -> int:
        """Find index of target in sorted array (-1 if not found)"""
        idx = bisect.bisect_left(arr, target)
        if idx < len(arr) and arr[idx] == target:
            return idx
        return -1

    @staticmethod
    def sort_ascending(arr: List) -> List:
        """Sort array in ascending order"""
        return sorted(arr)

    @staticmethod
    def sort_descending(arr: List) -> List:
        """Sort array in descending order"""
        return sorted(arr, reverse=True)

    @staticmethod
    def sort_by_key(arr: List, key_func: Callable) -> List:
        """Sort array by custom key function"""
        return sorted(arr, key=key_func)

    # ========================================================================
    # ARRAY OPERATIONS (8 primitives)
    # ========================================================================

    @staticmethod
    def find_max(arr: List) -> Any:
        """Find maximum element"""
        return max(arr) if arr else None

    @staticmethod
    def find_min(arr: List) -> Any:
        """Find minimum element"""
        return min(arr) if arr else None

    @staticmethod
    def count_if(arr: List, condition: Callable) -> int:
        """Count elements satisfying condition"""
        return sum(1 for x in arr if condition(x))

    @staticmethod
    def filter_by(arr: List, condition: Callable) -> List:
        """Filter elements by condition"""
        return [x for x in arr if condition(x)]

    @staticmethod
    def map_transform(arr: List, func: Callable) -> List:
        """Transform each element"""
        return [func(x) for x in arr]

    @staticmethod
    def cumulative_sum(arr: List[int]) -> List[int]:
        """Compute cumulative sum (running total)"""
        if not arr:
            return []
        result = [arr[0]]
        for i in range(1, len(arr)):
            result.append(result[-1] + arr[i])
        return result

    @staticmethod
    def sliding_window_max(arr: List[int], k: int) -> List[int]:
        """Maximum in each window of size k"""
        if not arr or k == 0:
            return []
        result = []
        dq = deque()  # Store indices

        for i in range(len(arr)):
            # Remove elements outside window
            while dq and dq[0] < i - k + 1:
                dq.popleft()

            # Remove elements smaller than current
            while dq and arr[dq[-1]] < arr[i]:
                dq.pop()

            dq.append(i)

            if i >= k - 1:
                result.append(arr[dq[0]])

        return result

    @staticmethod
    def two_pointers_pair_sum(arr: List[int], target: int) -> Tuple[int, int]:
        """Find pair with given sum using two pointers (array must be sorted)"""
        left, right = 0, len(arr) - 1

        while left < right:
            current_sum = arr[left] + arr[right]
            if current_sum == target:
                return (left, right)
            elif current_sum < target:
                left += 1
            else:
                right -= 1

        return (-1, -1)

    # ========================================================================
    # STRING OPERATIONS (5 primitives)
    # ========================================================================

    @staticmethod
    def string_reverse(s: str) -> str:
        """Reverse string"""
        return s[::-1]

    @staticmethod
    def string_split(s: str, delim: str = ' ') -> List[str]:
        """Split string by delimiter"""
        return s.split(delim)

    @staticmethod
    def string_join(arr: List[str], delim: str = '') -> str:
        """Join strings with delimiter"""
        return delim.join(arr)

    @staticmethod
    def string_count(s: str, char: str) -> int:
        """Count occurrences of character"""
        return s.count(char)

    @staticmethod
    def string_is_palindrome(s: str) -> bool:
        """Check if string is palindrome"""
        return s == s[::-1]

    # ========================================================================
    # GRAPH ALGORITHMS (8 primitives)
    # ========================================================================

    @staticmethod
    def graph_adjacency_list_from_edges(edges: List[Tuple[int, int]], n: int, directed=False) -> List[List[int]]:
        """Build adjacency list from edge list"""
        adj = [[] for _ in range(n)]
        for u, v in edges:
            adj[u].append(v)
            if not directed:
                adj[v].append(u)
        return adj

    @staticmethod
    def graph_bfs(adj: List[List[int]], start: int) -> List[int]:
        """BFS traversal, returns nodes in visit order"""
        n = len(adj)
        visited = [False] * n
        queue = deque([start])
        visited[start] = True
        result = []

        while queue:
            u = queue.popleft()
            result.append(u)

            for v in adj[u]:
                if not visited[v]:
                    visited[v] = True
                    queue.append(v)

        return result

    @staticmethod
    def graph_dfs(adj: List[List[int]], start: int) -> List[int]:
        """DFS traversal, returns nodes in visit order"""
        n = len(adj)
        visited = [False] * n
        result = []

        def dfs_helper(u):
            visited[u] = True
            result.append(u)
            for v in adj[u]:
                if not visited[v]:
                    dfs_helper(v)

        dfs_helper(start)
        return result

    @staticmethod
    def graph_shortest_path_unweighted(adj: List[List[int]], start: int, end: int) -> int:
        """Shortest path length in unweighted graph (-1 if no path)"""
        n = len(adj)
        dist = [-1] * n
        dist[start] = 0
        queue = deque([start])

        while queue:
            u = queue.popleft()
            if u == end:
                return dist[end]

            for v in adj[u]:
                if dist[v] == -1:
                    dist[v] = dist[u] + 1
                    queue.append(v)

        return dist[end]

    @staticmethod
    def graph_connected_components(adj: List[List[int]]) -> int:
        """Count number of connected components"""
        n = len(adj)
        visited = [False] * n
        components = 0

        def dfs(u):
            visited[u] = True
            for v in adj[u]:
                if not visited[v]:
                    dfs(v)

        for i in range(n):
            if not visited[i]:
                dfs(i)
                components += 1

        return components

    @staticmethod
    def graph_is_bipartite(adj: List[List[int]]) -> bool:
        """Check if graph is bipartite (2-colorable)"""
        n = len(adj)
        color = [-1] * n

        def bfs(start):
            queue = deque([start])
            color[start] = 0

            while queue:
                u = queue.popleft()
                for v in adj[u]:
                    if color[v] == -1:
                        color[v] = 1 - color[u]
                        queue.append(v)
                    elif color[v] == color[u]:
                        return False
            return True

        for i in range(n):
            if color[i] == -1:
                if not bfs(i):
                    return False

        return True

    @staticmethod
    def graph_topological_sort(adj: List[List[int]]) -> List[int]:
        """Topological sort (returns [] if cycle exists)"""
        n = len(adj)
        in_degree = [0] * n

        for u in range(n):
            for v in adj[u]:
                in_degree[v] += 1

        queue = deque([i for i in range(n) if in_degree[i] == 0])
        result = []

        while queue:
            u = queue.popleft()
            result.append(u)

            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        return result if len(result) == n else []

    @staticmethod
    def graph_has_cycle(adj: List[List[int]], directed=True) -> bool:
        """Check if graph has cycle"""
        n = len(adj)

        if directed:
            # DFS with recursion stack for directed graph
            visited = [False] * n
            rec_stack = [False] * n

            def dfs(u):
                visited[u] = True
                rec_stack[u] = True

                for v in adj[u]:
                    if not visited[v]:
                        if dfs(v):
                            return True
                    elif rec_stack[v]:
                        return True

                rec_stack[u] = False
                return False

            for i in range(n):
                if not visited[i]:
                    if dfs(i):
                        return True
            return False
        else:
            # DFS with parent tracking for undirected graph
            visited = [False] * n

            def dfs(u, parent):
                visited[u] = True
                for v in adj[u]:
                    if not visited[v]:
                        if dfs(v, u):
                            return True
                    elif v != parent:
                        return True
                return False

            for i in range(n):
                if not visited[i]:
                    if dfs(i, -1):
                        return True
            return False

    # ========================================================================
    # DYNAMIC PROGRAMMING (6 primitives)
    # ========================================================================

    @staticmethod
    def dp_fibonacci(n: int) -> int:
        """Compute nth Fibonacci number"""
        if n <= 1:
            return n

        dp = [0] * (n + 1)
        dp[1] = 1

        for i in range(2, n + 1):
            dp[i] = dp[i-1] + dp[i-2]

        return dp[n]

    @staticmethod
    def dp_max_subarray_sum(arr: List[int]) -> int:
        """Maximum subarray sum (Kadane's algorithm)"""
        if not arr:
            return 0

        max_ending_here = max_so_far = arr[0]

        for i in range(1, len(arr)):
            max_ending_here = max(arr[i], max_ending_here + arr[i])
            max_so_far = max(max_so_far, max_ending_here)

        return max_so_far

    @staticmethod
    def dp_longest_increasing_subsequence(arr: List[int]) -> int:
        """Length of longest increasing subsequence"""
        if not arr:
            return 0

        n = len(arr)
        dp = [1] * n

        for i in range(1, n):
            for j in range(i):
                if arr[j] < arr[i]:
                    dp[i] = max(dp[i], dp[j] + 1)

        return max(dp)

    @staticmethod
    def dp_coin_change(coins: List[int], amount: int) -> int:
        """Minimum coins to make amount (-1 if impossible)"""
        dp = [float('inf')] * (amount + 1)
        dp[0] = 0

        for i in range(1, amount + 1):
            for coin in coins:
                if coin <= i:
                    dp[i] = min(dp[i], dp[i - coin] + 1)

        return dp[amount] if dp[amount] != float('inf') else -1

    @staticmethod
    def dp_knapsack_01(weights: List[int], values: List[int], capacity: int) -> int:
        """0-1 Knapsack problem"""
        n = len(weights)
        dp = [[0 for _ in range(capacity + 1)] for _ in range(n + 1)]

        for i in range(1, n + 1):
            for w in range(1, capacity + 1):
                if weights[i-1] <= w:
                    dp[i][w] = max(
                        values[i-1] + dp[i-1][w - weights[i-1]],
                        dp[i-1][w]
                    )
                else:
                    dp[i][w] = dp[i-1][w]

        return dp[n][capacity]

    @staticmethod
    def dp_longest_common_subsequence(s1: str, s2: str) -> int:
        """Length of longest common subsequence"""
        m, n = len(s1), len(s2)
        dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        return dp[m][n]

    # ========================================================================
    # GREEDY ALGORITHMS (4 primitives)
    # ========================================================================

    @staticmethod
    def greedy_activity_selection(start: List[int], end: List[int]) -> int:
        """Maximum non-overlapping activities"""
        activities = sorted(zip(start, end), key=lambda x: x[1])
        count = 0
        last_end = -1

        for s, e in activities:
            if s >= last_end:
                count += 1
                last_end = e

        return count

    @staticmethod
    def greedy_minimum_coins(coins: List[int], amount: int) -> int:
        """Minimum coins (greedy, assumes canonical coin system)"""
        coins = sorted(coins, reverse=True)
        count = 0

        for coin in coins:
            if amount >= coin:
                count += amount // coin
                amount %= coin

        return count if amount == 0 else -1

    @staticmethod
    def greedy_fractional_knapsack(weights: List[float], values: List[float], capacity: float) -> float:
        """Fractional knapsack (greedy by value/weight ratio)"""
        items = [(v/w, w, v) for v, w in zip(values, weights)]
        items.sort(reverse=True)

        total_value = 0.0
        remaining = capacity

        for ratio, weight, value in items:
            if remaining >= weight:
                total_value += value
                remaining -= weight
            else:
                total_value += ratio * remaining
                break

        return total_value

    @staticmethod
    def greedy_huffman_encoding(frequencies: Dict[str, int]) -> Dict[str, str]:
        """Huffman encoding (optimal prefix codes)"""
        import heapq

        # Build Huffman tree
        heap = [[freq, [char, ""]] for char, freq in frequencies.items()]
        heapq.heapify(heap)

        while len(heap) > 1:
            lo = heapq.heappop(heap)
            hi = heapq.heappop(heap)

            for pair in lo[1:]:
                pair[1] = '0' + pair[1]
            for pair in hi[1:]:
                pair[1] = '1' + pair[1]

            heapq.heappush(heap, [lo[0] + hi[0]] + lo[1:] + hi[1:])

        # Extract codes
        codes = {char: code for char, code in heap[0][1:]}
        return codes

    # ========================================================================
    # MATH & NUMBER THEORY (4 primitives)
    # ========================================================================

    @staticmethod
    def math_gcd(a: int, b: int) -> int:
        """Greatest common divisor"""
        while b:
            a, b = b, a % b
        return a

    @staticmethod
    def math_lcm(a: int, b: int) -> int:
        """Least common multiple"""
        return abs(a * b) // IOIPrimitives.math_gcd(a, b)

    @staticmethod
    def math_is_prime(n: int) -> bool:
        """Check if number is prime"""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False

        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return False

        return True

    @staticmethod
    def math_prime_factorization(n: int) -> Dict[int, int]:
        """Prime factorization (returns {prime: count})"""
        factors = {}
        d = 2

        while d * d <= n:
            while n % d == 0:
                factors[d] = factors.get(d, 0) + 1
                n //= d
            d += 1

        if n > 1:
            factors[n] = factors.get(n, 0) + 1

        return factors


# ============================================================================
# EXAMPLE USAGE & TESTS
# ============================================================================

if __name__ == "__main__":
    print("Testing IOI Primitives...")

    # Test array operations
    arr = [3, 1, 4, 1, 5, 9, 2, 6]
    print(f"Original array: {arr}")
    print(f"Max: {IOIPrimitives.find_max(arr)}")
    print(f"Sorted: {IOIPrimitives.sort_ascending(arr)}")
    print(f"Count even: {IOIPrimitives.count_if(arr, lambda x: x % 2 == 0)}")

    # Test graph algorithms
    edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    adj = IOIPrimitives.graph_adjacency_list_from_edges(edges, 4)
    print(f"\nGraph adjacency list: {adj}")
    print(f"BFS from 0: {IOIPrimitives.graph_bfs(adj, 0)}")
    print(f"Has cycle: {IOIPrimitives.graph_has_cycle(adj, directed=False)}")

    # Test DP
    print(f"\nFibonacci(10): {IOIPrimitives.dp_fibonacci(10)}")
    print(f"Max subarray sum [−2,1,−3,4,−1,2,1,−5,4]: {IOIPrimitives.dp_max_subarray_sum([-2,1,-3,4,-1,2,1,-5,4])}")

    print("\n✅ All primitives loaded successfully!")
