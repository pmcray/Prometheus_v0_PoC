#!/usr/bin/env python3
"""
IOI Code Synthesizer (v0.75)

Uses Google Gemini to synthesize Python code from algorithm primitives.
Combines LLM generation with evolutionary search over primitive sequences.
"""

import os
import json
from typing import List, Dict, Tuple
import google.generativeai as genai
from ioi_primitives import IOIPrimitives

class IOICodeSynthesizer:
    """Generate Python code from algorithm primitives using LLM"""

    def __init__(self, api_key: str = None):
        """Initialize with Gemini API"""
        if api_key is None:
            api_key = os.environ.get('GOOGLE_API_KEY')

        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set. Set via environment or parameter.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.primitives = IOIPrimitives()

        # Cache primitive implementations as strings
        self.primitive_code_cache = self._build_primitive_code_cache()

    def _build_primitive_code_cache(self) -> Dict[str, str]:
        """Extract source code for each primitive"""
        import inspect

        cache = {}

        # Get all methods from IOIPrimitives
        for name, method in inspect.getmembers(IOIPrimitives, predicate=inspect.isfunction):
            if name.startswith('_'):
                continue

            # Get source code
            try:
                source = inspect.getsource(method)
                cache[name] = source
            except (OSError, TypeError):
                pass

        return cache

    def _get_primitive_implementations(self, primitive_names: List[str]) -> str:
        """Get source code for specified primitives"""
        code_blocks = []

        for name in primitive_names:
            if name in self.primitive_code_cache:
                code_blocks.append(f"# Primitive: {name}")
                code_blocks.append(self.primitive_code_cache[name])
                code_blocks.append("")

        return "\n".join(code_blocks)

    def synthesize(self,
                   problem_text: str,
                   examples: List[Dict],
                   algorithm_sequence: List[str],
                   constraints: Dict = None) -> str:
        """
        Synthesize Python code for a competitive programming problem.

        Args:
            problem_text: Problem description
            examples: List of {'input': str, 'output': str} dicts
            algorithm_sequence: List of primitive names to use
            constraints: Dict with keys like 'n_max', 'time_limit_ms', etc.

        Returns:
            Complete Python code as string
        """

        # Get primitive implementations
        primitive_code = self._get_primitive_implementations(algorithm_sequence)

        # Format examples
        examples_str = self._format_examples(examples)

        # Format constraints
        constraints_str = self._format_constraints(constraints) if constraints else "None specified"

        # Build prompt
        prompt = self._build_synthesis_prompt(
            problem_text,
            examples_str,
            primitive_code,
            algorithm_sequence,
            constraints_str
        )

        # Generate code
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more deterministic code
                    max_output_tokens=2048,
                )
            )

            code = self._extract_code(response.text)
            return code

        except Exception as e:
            print(f"Error generating code: {e}")
            return self._generate_fallback_code(algorithm_sequence)

    def _format_examples(self, examples: List[Dict]) -> str:
        """Format examples for prompt"""
        formatted = []
        for i, ex in enumerate(examples[:3], 1):  # Limit to 3 examples
            formatted.append(f"Example {i}:")
            formatted.append(f"Input:\n{ex['input']}")
            formatted.append(f"Output:\n{ex['output']}")
            formatted.append("")

        return "\n".join(formatted)

    def _format_constraints(self, constraints: Dict) -> str:
        """Format constraints for prompt"""
        lines = []
        for key, value in constraints.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _build_synthesis_prompt(self,
                                problem_text: str,
                                examples_str: str,
                                primitive_code: str,
                                algorithm_sequence: List[str],
                                constraints_str: str) -> str:
        """Build the complete synthesis prompt with few-shot examples"""

        # Few-shot examples to guide generation
        few_shot_examples = """
EXAMPLE 1 - Count Even Numbers:
Problem: Count how many even numbers are in an array.
Input format: First line N, second line N integers
Output: Single integer

Solution:
```python
n = int(input())
arr = list(map(int, input().split()))
count = sum(1 for x in arr if x % 2 == 0)
print(count)
```

EXAMPLE 2 - Find Maximum:
Problem: Find the maximum element in an array.
Input format: First line N, second line N integers
Output: Single integer

Solution:
```python
n = int(input())
arr = list(map(int, input().split()))
print(max(arr))
```

EXAMPLE 3 - Sum of Array:
Problem: Calculate the sum of all elements.
Input format: First line N, second line N integers
Output: Single integer

Solution:
```python
n = int(input())
arr = list(map(int, input().split()))
print(sum(arr))
```
"""

        prompt = f"""You are an expert competitive programmer solving USACO Bronze level problems.

{few_shot_examples}

NOW SOLVE THIS PROBLEM:

PROBLEM:
{problem_text}

EXAMPLES:
{examples_str}

CONSTRAINTS:
{constraints_str}

SUGGESTED ALGORITHMS:
Use these algorithms in your solution: {', '.join(algorithm_sequence)}

AVAILABLE PRIMITIVE IMPLEMENTATIONS:
{primitive_code}

CRITICAL REQUIREMENTS:
1. Read input EXACTLY as specified in the problem format
2. Output EXACTLY matches expected format (no extra text, proper spacing)
3. Use the suggested algorithms: {', '.join(algorithm_sequence)}
4. Handle edge cases: empty arrays, single elements, all same values
5. Ensure O(n) or better time complexity for arrays
6. Write production-quality code with clear variable names
7. DO NOT print debugging information
8. DO NOT include test cases or main() wrapper unless specified
9. Code must be complete and immediately executable

COMMON PATTERNS FOR BRONZE PROBLEMS:
- Array input: n = int(input()); arr = list(map(int, input().split()))
- Single output: print(result)
- Multiple outputs: print(' '.join(map(str, results))) or multiple print() calls
- String processing: s = input().strip()
- Edge case: always check if array is empty or has 1 element

OUTPUT FORMAT:
Provide ONLY the Python code between triple backticks. No explanations before or after.

```python
# Your complete solution here
```
"""

        return prompt

    def _extract_code(self, response_text: str) -> str:
        """Extract Python code from LLM response"""
        # Try to find code block
        if '```python' in response_text:
            start = response_text.find('```python') + 9
            end = response_text.find('```', start)
            if end != -1:
                return response_text[start:end].strip()

        # Try to find any code block
        if '```' in response_text:
            start = response_text.find('```') + 3
            end = response_text.find('```', start)
            if end != -1:
                return response_text[start:end].strip()

        # Return entire response if no code blocks found
        return response_text.strip()

    def _generate_fallback_code(self, algorithm_sequence: List[str]) -> str:
        """Generate simple fallback code if LLM fails"""
        return f"""# Fallback solution
import sys

def solve():
    # Read input
    n = int(input())
    arr = list(map(int, input().split()))

    # Process using: {', '.join(algorithm_sequence)}
    result = arr[0] if arr else 0

    print(result)

if __name__ == "__main__":
    solve()
"""

    def synthesize_multiple(self,
                           problem_text: str,
                           examples: List[Dict],
                           algorithm_sequences: List[List[str]],
                           constraints: Dict = None,
                           max_attempts: int = 5) -> List[Tuple[str, List[str]]]:
        """
        Generate multiple code solutions using different algorithm sequences.

        Returns:
            List of (code, algorithm_sequence) tuples
        """
        solutions = []

        for i, seq in enumerate(algorithm_sequences[:max_attempts]):
            try:
                code = self.synthesize(problem_text, examples, seq, constraints)
                solutions.append((code, seq))
            except Exception as e:
                print(f"Failed to generate solution {i+1}: {e}")
                continue

        return solutions


class ProblemClassifier:
    """Classify IOI problems by category and suggest algorithms"""

    def __init__(self, api_key: str = None):
        """Initialize with Gemini API"""
        if api_key is None:
            api_key = os.environ.get('GOOGLE_API_KEY')

        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def classify(self, problem_text: str, examples: List[Dict] = None) -> Dict:
        """
        Classify problem and suggest algorithms.

        Returns:
            {
                'categories': ['array', 'sorting', 'greedy'],
                'algorithms': ['sort_ascending', 'greedy_activity_selection'],
                'complexity': 'O(n log n)',
                'difficulty': 'bronze',
                'constraints': {'n_max': 1000, 'time_limit_ms': 2000}
            }
        """

        examples_str = ""
        if examples:
            examples_str = "\n\nEXAMPLES:\n"
            for i, ex in enumerate(examples[:2], 1):
                examples_str += f"Input: {ex['input']}\nOutput: {ex['output']}\n"

        prompt = f"""Analyze this USACO Bronze competitive programming problem and classify it.

PROBLEM:
{problem_text}
{examples_str}

CLASSIFICATION EXAMPLES:

Example 1:
Problem: "Count how many even numbers are in an array"
→ Categories: ["array", "math"]
→ Algorithms: ["use_array", "count_if"]
→ Complexity: "O(n)"

Example 2:
Problem: "Find the maximum sum of any contiguous subarray"
→ Categories: ["array", "dp"]
→ Algorithms: ["use_array", "dp_max_subarray_sum"]
→ Complexity: "O(n)"

Example 3:
Problem: "Sort an array and find the median"
→ Categories: ["array", "sorting"]
→ Algorithms: ["use_array", "sort_ascending", "find_median"]
→ Complexity: "O(n log n)"

NOW CLASSIFY THE GIVEN PROBLEM:

Provide analysis in JSON format with these exact keys:
{{
    "categories": ["primary category first", "secondary..."],
    "algorithms": ["3-5 most relevant primitive names"],
    "complexity": "expected time complexity",
    "difficulty": "bronze",
    "constraints": {{"n_max": 1000, "time_limit_ms": 2000}}
}}

AVAILABLE IOI PRIMITIVES (choose 3-5 most relevant):

📦 Data Structures:
- use_array, use_2d_array, use_dict, use_set, use_heap, use_queue, use_stack
- use_frequency_map, use_prefix_sum

🔍 Search & Sort:
- linear_search, binary_search, sort_ascending, sort_descending, sort_by_key

📊 Array Operations:
- find_max, find_min, count_if, filter_by, map_transform
- cumulative_sum, sliding_window_max, two_pointers_pair_sum

📝 String Operations:
- string_reverse, string_split, string_join, string_count, string_is_palindrome

🌐 Graph Algorithms:
- graph_adjacency_list_from_edges, graph_bfs, graph_dfs
- graph_shortest_path_unweighted, graph_connected_components
- graph_is_bipartite, graph_topological_sort, graph_has_cycle

💡 Dynamic Programming:
- dp_fibonacci, dp_max_subarray_sum, dp_longest_increasing_subsequence
- dp_coin_change, dp_knapsack_01, dp_longest_common_subsequence

🎯 Greedy Algorithms:
- greedy_activity_selection, greedy_minimum_coins
- greedy_fractional_knapsack, greedy_huffman_encoding

🔢 Math:
- math_gcd, math_lcm, math_is_prime, math_prime_factorization

IMPORTANT:
- Choose algorithms that directly solve the problem
- For simple problems, use 2-3 basic primitives
- For complex problems, use 4-5 including advanced ones
- Prefer simpler algorithms for Bronze level

Output ONLY the JSON, no explanations:
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=512,
                )
            )

            # Extract JSON
            text = response.text.strip()
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                text = text[start:end].strip()
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                text = text[start:end].strip()

            result = json.loads(text)
            return result

        except Exception as e:
            print(f"Classification error: {e}")
            # Return default classification
            return {
                'categories': ['simulation'],
                'algorithms': ['use_array', 'find_max'],
                'complexity': 'O(n)',
                'difficulty': 'bronze',
                'constraints': {'n_max': 1000, 'time_limit_ms': 2000}
            }


# ============================================================================
# EXAMPLE USAGE & TESTS
# ============================================================================

if __name__ == "__main__":
    print("Testing IOI Code Synthesizer...")

    # Check API key
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not set. Set it with:")
        print("   export GOOGLE_API_KEY='your_key_here'")
        exit(1)

    # Initialize
    classifier = ProblemClassifier(api_key)
    synthesizer = IOICodeSynthesizer(api_key)

    # Example problem
    problem = """
    Count Even Numbers

    You are given an array of N integers. Count how many of them are even.

    Input:
    - First line: N (1 ≤ N ≤ 1000)
    - Second line: N space-separated integers (each between 1 and 10^9)

    Output:
    - A single integer: the count of even numbers
    """

    examples = [
        {
            'input': '5\n2 4 6 8 10',
            'output': '5'
        },
        {
            'input': '3\n1 3 5',
            'output': '0'
        },
        {
            'input': '4\n1 2 3 4',
            'output': '2'
        }
    ]

    # Test classifier
    print("\n📊 Classifying problem...")
    classification = classifier.classify(problem, examples)
    print(f"Categories: {classification['categories']}")
    print(f"Suggested algorithms: {classification['algorithms']}")
    print(f"Difficulty: {classification['difficulty']}")

    # Test synthesizer
    print("\n💻 Synthesizing code...")
    code = synthesizer.synthesize(
        problem,
        examples,
        classification['algorithms'][:3],  # Use top 3 suggested algorithms
        classification['constraints']
    )

    print("\n" + "="*70)
    print("GENERATED CODE:")
    print("="*70)
    print(code)
    print("="*70)

    # Test the generated code
    print("\n🧪 Testing generated code...")
    import subprocess
    import tempfile

    # Write code to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        code_file = f.name

    # Test on example 1
    try:
        result = subprocess.run(
            ['python3', code_file],
            input=examples[0]['input'],
            capture_output=True,
            timeout=2,
            text=True
        )
        output = result.stdout.strip()
        expected = examples[0]['output'].strip()

        if output == expected:
            print(f"✅ Test 1 PASSED: {output} == {expected}")
        else:
            print(f"❌ Test 1 FAILED: {output} != {expected}")

    except subprocess.TimeoutExpired:
        print("❌ Test 1 TIMEOUT")
    except Exception as e:
        print(f"❌ Test 1 ERROR: {e}")

    # Clean up
    os.unlink(code_file)

    print("\n✅ Synthesizer test complete!")
