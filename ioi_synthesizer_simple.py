#!/usr/bin/env python3
"""
Simplified IOI Code Synthesizer for Small Models (v0.77)
Optimized for DeepSeek-Coder-1.3B and similar small models
"""

import os
import re
import json
from typing import List, Dict, Optional
from pathlib import Path
import subprocess
import tempfile

# Import local model interface from main synthesizer
from ioi_synthesizer_local import LocalModelInference

class SimpleIOICodeSynthesizer:
    """Simplified code synthesizer optimized for small (1-2B) models"""

    def __init__(self, local_model_path: str):
        """
        Args:
            local_model_path: Path to local GGUF model
        """
        print(f"🔧 Initializing simple synthesizer: {local_model_path}")
        self.local_model = LocalModelInference(local_model_path)

        if not self.local_model.available:
            raise RuntimeError("llama-cli not found. Install llama.cpp first.")

        print(f"✅ Simple synthesizer ready")

    def synthesize(self,
                  problem_text: str,
                  examples: List[Dict],
                  algorithm_hints: List[str] = None) -> str:
        """
        Generate code with simplified prompt.

        Args:
            problem_text: Problem description
            examples: List of {'input': str, 'output': str}
            algorithm_hints: Optional algorithm suggestions (ignored for simplicity)

        Returns:
            Python code as string
        """
        prompt = self._build_simple_prompt(problem_text, examples)

        # Generate with higher temperature for more creativity
        response_text = self.local_model.generate(
            prompt,
            temperature=0.5,  # Higher than 0.3
            max_tokens=1024   # Shorter than 2048
        )

        # Extract code
        code = self._extract_code(response_text)
        return code

    def _build_simple_prompt(self, problem_text: str, examples: List[Dict]) -> str:
        """Build minimal prompt for small models"""

        # Only show 1 example to save context
        examples_text = ""
        if examples:
            ex = examples[0]
            examples_text = f"""
Example:
Input: {ex['input']}
Output: {ex['output']}
"""

        prompt = f"""Solve this programming problem in Python.

Problem: {problem_text}
{examples_text}

Write clean Python code that:
1. Reads input exactly as shown
2. Prints output exactly as shown
3. Uses simple Python (no type hints, no imports unless needed)
4. Handles edge cases

Code:
```python
"""

        return prompt

    def _extract_code(self, response_text: str) -> str:
        """Extract Python code from response"""
        # Remove trailing "```" if present
        text = response_text.strip()
        if text.endswith('```'):
            text = text[:-3].strip()

        # Try to find code block with python marker
        code_match = re.search(r'```python\n(.*?)```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Try to find code without python marker
        code_match = re.search(r'```\n(.*?)```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Look for code before "Explanation:" or similar
        if 'Explanation:' in text:
            text = text.split('Explanation:')[0].strip()
        if '[end of text]' in text:
            text = text.split('[end of text]')[0].strip()

        # If no markers, look for code starting with common patterns
        lines = text.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            # Stop at explanation markers
            if 'Explanation' in line or 'Note:' in line or '[end' in line:
                break

            # Start collecting when we see typical Python code
            if not in_code and (line.startswith('n = ') or
                               line.startswith('arr = ') or
                               line.startswith('def ') or
                               'input()' in line):
                in_code = True

            if in_code:
                code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines).strip()

        # Last resort: return full response
        return text


class SimpleProblemClassifier:
    """Simplified classifier using heuristics instead of LLM"""

    def classify(self, problem_text: str, examples: List[Dict] = None) -> Dict:
        """
        Fast heuristic classification (no LLM needed).

        Returns:
            {
                'categories': List[str],
                'algorithms': List[str],
            }
        """
        text_lower = problem_text.lower()

        categories = []
        algorithms = []

        # Detect categories
        if 'array' in text_lower or 'list' in text_lower or 'numbers' in text_lower:
            categories.append('array')
            algorithms.append('use_array')

        if 'string' in text_lower or 'character' in text_lower:
            categories.append('string')

        if 'sort' in text_lower:
            categories.append('sorting')
            algorithms.append('sort_ascending')

        # Detect operations
        if 'count' in text_lower:
            algorithms.append('count_if')

        if 'maximum' in text_lower or 'largest' in text_lower:
            algorithms.append('find_max')

        if 'minimum' in text_lower or 'smallest' in text_lower:
            algorithms.append('find_min')

        if 'sum' in text_lower:
            algorithms.append('cumulative_sum')

        if 'reverse' in text_lower:
            if 'string' in categories:
                algorithms.append('string_reverse')
            else:
                algorithms.append('use_array')

        # Defaults
        if not categories:
            categories = ['general']

        if not algorithms:
            algorithms = ['use_array', 'count_if']

        return {
            'categories': categories,
            'algorithms': algorithms[:3],  # Max 3
            'complexity': 'O(n)',
        }


if __name__ == "__main__":
    print("Simple IOI Code Synthesizer (v0.77)")
    print("=" * 70)

    # Check model
    model_path = os.environ.get('IOI_LOCAL_MODEL')
    if not model_path or not Path(model_path).exists():
        print(f"❌ Model not found: {model_path}")
        print("Set IOI_LOCAL_MODEL environment variable")
        exit(1)

    print(f"✅ Model: {model_path}")

    # Test synthesizer
    synthesizer = SimpleIOICodeSynthesizer(model_path)
    classifier = SimpleProblemClassifier()

    # Test problem
    problem = {
        'text': "Count how many even numbers are in the array",
        'examples': [
            {'input': '5\\n2 4 6 8 10', 'output': '5'},
            {'input': '3\\n1 3 5', 'output': '0'}
        ]
    }

    print("\n🧪 Testing synthesis...")
    print(f"Problem: {problem['text']}")

    classification = classifier.classify(problem['text'])
    print(f"Categories: {classification['categories']}")
    print(f"Algorithms: {classification['algorithms']}")

    print("\n💻 Generating code...")
    import time
    start = time.time()

    code = synthesizer.synthesize(
        problem['text'],
        problem['examples'],
        classification['algorithms']
    )

    elapsed = time.time() - start
    print(f"✅ Generated in {elapsed:.1f}s")

    print("\nGenerated code:")
    print("-" * 70)
    print(code)
    print("-" * 70)
