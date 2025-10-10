# IOI Bronze System Design (v0.75)

## Date: October 10, 2025

---

## Goal

Solve **40% of IOI Bronze-level problems** (easy subtasks) through:
1. Algorithm primitive library
2. Genetic search over algorithm combinations
3. LLM-based code synthesis
4. Automated testing and verification

---

## IOI Bronze Problem Characteristics

**Typical Bronze problems**:
- Input size: N ≤ 1000
- Time limit: 1-2 seconds
- Algorithms: Basic data structures + simple algorithms
- Patterns: Simulation, greedy, basic DP, graph traversal

**Example problems**:
- Count elements satisfying condition
- Find maximum/minimum value
- Sort and search
- Basic graph traversal (BFS/DFS)
- Simple dynamic programming (1D DP)

---

## Architecture

```
Problem → Parse → Classify → Select Algorithms → Synthesize Code → Test → Verify
  ↓         ↓        ↓             ↓                   ↓             ↓       ↓
 Text     AST    Category    Primitives         Python Code     Auto     Pass/
                                                                Tests    Fail
```

### Components

1. **Problem Parser**: Extract constraints, input/output format
2. **Problem Classifier**: Identify problem type (simulation, search, DP, etc.)
3. **Algorithm Selector**: Choose relevant primitives via genetic search
4. **Code Synthesizer**: Generate Python code using LLM (Gemini)
5. **Test Generator**: Create test cases from examples + edge cases
6. **Verifier**: Run code, check correctness + time/space complexity

---

## Primitive Library (50 Algorithms)

### Data Structures (10)
```python
class Primitives:
    # Basic structures
    def use_array(self, n): return [0] * n
    def use_dict(self): return {}
    def use_set(self): return set()
    def use_heap(self): return []  # heapq
    def use_queue(self): return collections.deque()

    # Advanced structures
    def use_prefix_sum(self, arr): return self._prefix_sum(arr)
    def use_frequency_map(self, arr): return Counter(arr)
    def use_sorted_list(self, arr): return sorted(arr)
    def use_stack(self): return []
    def use_2d_array(self, n, m): return [[0]*m for _ in range(n)]
```

### Algorithms (40)

#### Searching & Sorting (5)
```python
    def linear_search(self, arr, target): ...
    def binary_search(self, arr, target): ...
    def sort_ascending(self, arr): return sorted(arr)
    def sort_descending(self, arr): return sorted(arr, reverse=True)
    def sort_by_key(self, arr, key_func): return sorted(arr, key=key_func)
```

#### Array Operations (8)
```python
    def find_max(self, arr): return max(arr)
    def find_min(self, arr): return min(arr)
    def count_if(self, arr, condition): return sum(1 for x in arr if condition(x))
    def filter_by(self, arr, condition): return [x for x in arr if condition(x)]
    def map_transform(self, arr, func): return [func(x) for x in arr]
    def cumulative_sum(self, arr): ...
    def sliding_window(self, arr, k): ...
    def two_pointers(self, arr, target): ...
```

#### String Operations (5)
```python
    def string_reverse(self, s): return s[::-1]
    def string_split(self, s, delim): return s.split(delim)
    def string_join(self, arr, delim): return delim.join(arr)
    def string_count(self, s, char): return s.count(char)
    def string_palindrome_check(self, s): return s == s[::-1]
```

#### Graph Algorithms (8)
```python
    def graph_bfs(self, adj, start): ...
    def graph_dfs(self, adj, start): ...
    def graph_shortest_path_unweighted(self, adj, start, end): ...
    def graph_connected_components(self, adj): ...
    def graph_is_bipartite(self, adj): ...
    def graph_topological_sort(self, adj): ...
    def graph_has_cycle(self, adj): ...
    def graph_adjacency_list_from_edges(self, edges, n): ...
```

#### Dynamic Programming (8)
```python
    def dp_1d_initialize(self, n, value=0): return [value] * n
    def dp_fibonacci(self, n): ...
    def dp_coin_change(self, coins, target): ...
    def dp_longest_increasing_subsequence(self, arr): ...
    def dp_max_subarray_sum(self, arr): ...  # Kadane
    def dp_knapsack_01(self, weights, values, capacity): ...
    def dp_edit_distance(self, s1, s2): ...
    def dp_longest_common_subsequence(self, s1, s2): ...
```

#### Greedy Algorithms (6)
```python
    def greedy_activity_selection(self, start, end): ...
    def greedy_interval_scheduling(self, intervals): ...
    def greedy_fractional_knapsack(self, weights, values, capacity): ...
    def greedy_huffman_encoding(self, frequencies): ...
    def greedy_minimum_coins(self, coins, amount): ...
    def greedy_maximum_meetings(self, start, end): ...
```

---

## Implementation Strategy

### Phase 1: Primitive Library (Day 1)
```python
# File: ioi_primitives.py

class IOIPrimitives:
    """Library of 50 algorithmic primitives for competitive programming"""

    def __init__(self):
        self.primitives = self._build_library()

    def _build_library(self):
        # Register all 50 primitives
        return {
            'array': [...],
            'search': [...],
            'graph': [...],
            'dp': [...],
            'greedy': [...],
        }
```

### Phase 2: Problem Classifier (Day 2)
```python
# File: ioi_classifier.py

class ProblemClassifier:
    """Classify IOI problems by type"""

    def classify(self, problem_text):
        """Returns: ['simulation', 'graph_bfs', 'dp_1d'] etc."""

        # Use LLM (Gemini) to classify
        prompt = f"""
        Classify this competitive programming problem.
        Return categories: [simulation, array, string, graph, dp, greedy, math]

        Problem: {problem_text}

        Output JSON: {{"categories": [...], "constraints": {{...}}}}
        """

        response = self.gemini.generate(prompt)
        return json.loads(response)
```

### Phase 3: Code Synthesizer (Day 3-4)
```python
# File: ioi_synthesizer.py

class CodeSynthesizer:
    """Generate Python code from algorithm primitives"""

    def synthesize(self, problem, algorithm_sequence):
        """
        Args:
            problem: Problem text + examples
            algorithm_sequence: ['prefix_sum', 'binary_search']

        Returns:
            Python code as string
        """

        # Build prompt with primitives
        primitive_code = self._get_primitive_implementations(algorithm_sequence)

        prompt = f"""
        Write Python code to solve this problem using these algorithms:

        Problem: {problem['text']}
        Examples: {problem['examples']}

        Available primitives:
        {primitive_code}

        Requirements:
        - Read input from stdin
        - Write output to stdout
        - Use the provided primitive functions
        - Handle edge cases
        - Time complexity: O(n log n) or better

        Output only the complete Python code.
        """

        code = self.gemini.generate(prompt, temperature=0.3)
        return code
```

### Phase 4: Genetic Search (Day 5)
```python
# File: ioi_evolution.py

class IOIEvolution:
    """Evolve algorithm sequences for problems"""

    def evolve(self, problem, max_generations=50):
        """Find best algorithm combination"""

        # Initialize population
        population = self._initialize_population(problem)

        for gen in range(max_generations):
            # Evaluate fitness
            fitnesses = []
            for individual in population:
                code = self.synthesizer.synthesize(problem, individual)
                score = self.tester.test(code, problem['test_cases'])
                fitnesses.append(score)

            # Early stopping
            if max(fitnesses) >= 0.99:
                break

            # Selection, crossover, mutation
            population = self._evolve_generation(population, fitnesses)

        # Return best
        best_idx = np.argmax(fitnesses)
        return population[best_idx], fitnesses[best_idx]
```

### Phase 5: Automated Tester (Day 6)
```python
# File: ioi_tester.py

class ProblemTester:
    """Test generated code"""

    def test(self, code, test_cases, timeout=2.0):
        """Run code on test cases with timeout"""

        correct = 0
        total = len(test_cases)

        for test_input, expected_output in test_cases:
            try:
                # Run code with timeout
                result = self._run_code(code, test_input, timeout)

                # Check correctness
                if self._compare_output(result, expected_output):
                    correct += 1

            except TimeoutError:
                pass  # TLE
            except Exception:
                pass  # Runtime error

        return correct / total

    def _run_code(self, code, input_data, timeout):
        """Execute code in subprocess with timeout"""
        import subprocess
        import tempfile

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            code_file = f.name

        # Run with timeout
        proc = subprocess.run(
            ['python3', code_file],
            input=input_data,
            capture_output=True,
            timeout=timeout,
            text=True
        )

        return proc.stdout
```

### Phase 6: Test Generator (Day 7)
```python
# File: ioi_test_generator.py

class TestGenerator:
    """Generate additional test cases"""

    def generate(self, problem, num_tests=20):
        """Create edge cases + random tests"""

        tests = []

        # Edge cases
        tests.extend(self._generate_edge_cases(problem))

        # Random cases
        for _ in range(num_tests):
            test_input = self._generate_random_input(problem['constraints'])
            tests.append(test_input)

        return tests

    def _generate_edge_cases(self, problem):
        """Min values, max values, boundary conditions"""
        n = problem['constraints']['n']

        return [
            self._make_input(n=1),      # Minimum
            self._make_input(n=n),      # Maximum
            self._make_input(n=2),      # Small
            self._make_input(n=n//2),   # Medium
        ]
```

---

## Example: Complete Workflow

### Problem
```
Count how many numbers in array are divisible by K.

Input:
- First line: N (array size)
- Second line: N integers
- Third line: K

Output:
- Single integer: count of numbers divisible by K

Example:
Input:
5
2 4 6 8 10
2

Output:
5
```

### Step 1: Classification
```python
classifier.classify(problem_text)
# Output: {
#   'categories': ['array', 'simulation'],
#   'constraints': {'n': 1000, 'values': 10000}
# }
```

### Step 2: Algorithm Selection (Genetic Search)
```python
# Generation 0: Random sequences
population = [
    ['use_array', 'count_if'],
    ['linear_search', 'find_max'],
    ['sort_ascending', 'filter_by'],
    ...
]

# Evaluation: Try each, measure fitness
# Best: ['use_array', 'count_if'] → 100% correct

# Early stop (found perfect solution)
```

### Step 3: Code Synthesis
```python
algorithm_sequence = ['use_array', 'count_if']

code = synthesizer.synthesize(problem, algorithm_sequence)
# Output:
"""
n = int(input())
arr = list(map(int, input().split()))
k = int(input())

count = sum(1 for x in arr if x % k == 0)
print(count)
"""
```

### Step 4: Testing
```python
test_cases = [
    ("5\n2 4 6 8 10\n2", "5"),
    ("3\n1 3 5\n2", "0"),
    ("1\n100\n100", "1"),
]

tester.test(code, test_cases)
# Output: 1.0 (100% correct)
```

---

## Evaluation Plan

### Benchmark: USACO Bronze Problems

**Dataset**: 50 USACO Bronze problems (2020-2024)
- Publicly available
- Well-defined inputs/outputs
- Bronze = beginner level (maps to IOI subtask 1)

**Target**: 20/50 (40%) solved correctly

### Metrics

1. **Correctness**: % of test cases passed
2. **Time complexity**: Within limits?
3. **Code quality**: Clean, readable
4. **Search efficiency**: Generations to solution

### Baseline Comparisons

| System | USACO Bronze | Method |
|--------|--------------|--------|
| Human beginner | 30-40% | Learning |
| GPT-4 (zero-shot) | 20-30% | Direct generation |
| AlphaCode | 50-60% | Fine-tuned model |
| **Our v0.75** | **40%** (target) | Primitives + evolution + LLM |

---

## Implementation Timeline

| Day | Task | Deliverable |
|-----|------|-------------|
| **1** | Implement 50 primitives | `ioi_primitives.py` |
| **2** | Build classifier | `ioi_classifier.py` |
| **3-4** | Code synthesizer (LLM) | `ioi_synthesizer.py` |
| **5** | Genetic evolution | `ioi_evolution.py` |
| **6** | Automated tester | `ioi_tester.py` |
| **7** | Test generator | `ioi_test_generator.py` |
| **8-9** | Integration & debugging | `prometheus_ioi_bronze.py` |
| **10-11** | Evaluation on 50 problems | Results + analysis |
| **12-14** | Documentation & iteration | Final report |

**Total**: 2 weeks

---

## Success Criteria

### Minimum (v0.75 Bronze)
- ✅ 20/50 USACO Bronze problems (40%)
- ✅ All test cases passed for solved problems
- ✅ No timeout errors
- ✅ Code is syntactically correct

### Stretch Goals
- 🎯 25/50 (50%) - competitive with GPT-4
- 🎯 Average <20 generations to find solution
- 🎯 Transfer learning: Solve similar problems faster

---

## Next Steps (Starting Now)

1. **Create primitive library** (today)
   - Implement 50 algorithms in `ioi_primitives.py`
   - Unit test each primitive

2. **Set up LLM integration** (today)
   - Test Gemini API for code synthesis
   - Validate prompt engineering

3. **Build classifier** (tomorrow)
   - Use Gemini to classify 10 sample problems
   - Refine prompt for accuracy

4. **Implement evolution** (day 3)
   - Genetic search over algorithm sequences
   - Test on 3-5 simple problems

5. **Full integration** (day 4-7)
   - Connect all components
   - End-to-end testing

6. **Benchmark** (day 8-10)
   - Run on 50 USACO Bronze problems
   - Analyze results, iterate

---

## Technical Decisions

### Why Python for generated code?
- Fast to write/test
- Rich standard library (heapq, bisect, collections)
- IOI allows Python in practice division

### Why Gemini for synthesis?
- Already integrated in project
- Good at code generation
- Free tier sufficient for testing

### Why genetic search?
- Proven effective in ARC-AGI (7.5%)
- Explores algorithm combinations systematically
- Can discover non-obvious sequences

### Why 50 primitives?
- Bronze problems use ~10-15 algorithm types
- 50 gives good coverage without overwhelming search space
- 50^3 = 125K combinations (searchable in 50 generations × 50 population)

---

## Risk Mitigation

### Risk: LLM generates incorrect code
**Mitigation**: Test on multiple test cases, use evolutionary search to try multiple prompts

### Risk: Search space too large (50^5 = 312M)
**Mitigation**: Limit to 3 primitives per solution (50^3 = 125K), use problem classification to prune

### Risk: Timeout on complex problems
**Mitigation**: Enforce O(n log n) complexity, reject inefficient algorithms early

### Risk: Can't parse problem text
**Mitigation**: Start with well-formatted USACO problems, expand later

---

## Future Extensions (v0.76+)

### v0.76: IOI Silver (60% medium problems)
- Add 30 advanced algorithms (Dijkstra, segment trees, etc.)
- Meta-learning: Learn from editorial solutions
- Optimize for harder constraints (N ≤ 10^6)

### v0.77: IOI Gold (30% hard problems)
- Novel algorithm synthesis (combine primitives in creative ways)
- Multi-stage solutions (precompute + query)
- Advanced data structures

### v0.78: Cross-domain transfer
- Use IOI algorithms for IMO combinatorics
- Graph algorithms → Geometry problems
- DP patterns → Physics optimization

---

*Generated: October 10, 2025*
*Prometheus v0.75: IOI Bronze System Design*
