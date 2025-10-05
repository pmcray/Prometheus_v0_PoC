"""
Causal Salience Model for Attention Head
Implements the trained causal attention mechanism from v0.47 workplan
"""

import ast
import re
import json
import pickle
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict, Counter

# Try to import ML libraries for token-level analysis
try:
    import tokenize
    from io import StringIO
    TOKENIZE_AVAILABLE = True
except ImportError:
    TOKENIZE_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available. Using simplified token analysis.")

@dataclass
class TokenImportance:
    """Token-level causal importance score"""
    token: str
    position: int
    importance_score: float
    causal_category: str  # 'control_flow', 'data_structure', 'algorithm', 'complexity_driver'
    explanation: str

@dataclass
class CausalSalienceMap:
    """Complete causal salience analysis for code"""
    code: str
    token_importances: List[TokenImportance]
    overall_complexity_driver: str
    confidence: float
    methodology: str

class CodeComplexityAnalyzer:
    """Analyzes code complexity patterns for training data generation"""

    def __init__(self):
        self.complexity_patterns = {
            'nested_loops': {
                'indicators': ['for.*for', 'while.*while', 'for.*while'],
                'complexity': 'O(n²)',
                'importance': 0.9
            },
            'single_loop': {
                'indicators': ['for ', 'while '],
                'complexity': 'O(n)',
                'importance': 0.7
            },
            'recursive_calls': {
                'indicators': ['def.*return.*\\('],
                'complexity': 'Variable',
                'importance': 0.8
            },
            'sorting': {
                'indicators': ['\\.sort\\(', 'sorted\\('],
                'complexity': 'O(n log n)',
                'importance': 0.8
            },
            'list_comprehension': {
                'indicators': ['\\[.*for.*in.*\\]'],
                'complexity': 'O(n)',
                'importance': 0.6
            }
        }

    def analyze_code_complexity(self, code: str) -> Dict[str, Any]:
        """Analyze code complexity patterns"""
        patterns_found = []

        for pattern_name, pattern_info in self.complexity_patterns.items():
            for indicator in pattern_info['indicators']:
                if re.search(indicator, code, re.MULTILINE):
                    patterns_found.append({
                        'pattern': pattern_name,
                        'complexity': pattern_info['complexity'],
                        'importance': pattern_info['importance']
                    })

        return {
            'patterns': patterns_found,
            'primary_complexity': patterns_found[0]['complexity'] if patterns_found else 'O(1)',
            'complexity_score': max([p['importance'] for p in patterns_found], default=0.1)
        }

class CausalDatasetGenerator:
    """Generates training dataset for causal salience model"""

    def __init__(self):
        self.complexity_analyzer = CodeComplexityAnalyzer()
        self.generated_samples = []

    def generate_training_data(self, num_samples: int = 2000) -> List[Dict[str, Any]]:
        """Generate training dataset with token-level causal annotations"""
        samples = []

        # Generate samples from templates
        templates = [
            self._generate_nested_loop_samples,
            self._generate_single_loop_samples,
            self._generate_sorting_samples,
            self._generate_search_samples,
            self._generate_recursive_samples
        ]

        samples_per_template = num_samples // len(templates)

        for template_func in templates:
            template_samples = template_func(samples_per_template)
            samples.extend(template_samples)

        logging.info(f"Generated {len(samples)} training samples")
        return samples

    def _generate_nested_loop_samples(self, count: int) -> List[Dict[str, Any]]:
        """Generate nested loop examples with annotations"""
        samples = []
        templates = [
            """def find_pairs(nums, target):
    for i in range(len(nums)):
        for j in range(i+1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return None""",

            """def matrix_multiply(A, B):
    result = []
    for i in range(len(A)):
        row = []
        for j in range(len(B[0])):
            row.append(sum(A[i][k] * B[k][j] for k in range(len(B))))
        result.append(row)
    return result""",

            """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr"""
        ]

        for i, template in enumerate(templates[:count]):
            annotations = self._annotate_nested_loops(template)
            samples.append({
                'code': template,
                'annotations': annotations,
                'complexity': 'O(n²)',
                'primary_drivers': ['nested_for_loops']
            })

        return samples

    def _generate_single_loop_samples(self, count: int) -> List[Dict[str, Any]]:
        """Generate single loop examples"""
        samples = []
        templates = [
            """def linear_search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1""",

            """def sum_array(arr):
    total = 0
    for num in arr:
        total += num
    return total""",

            """def reverse_array(arr):
    result = []
    for i in range(len(arr)-1, -1, -1):
        result.append(arr[i])
    return result"""
        ]

        for i, template in enumerate(templates[:count]):
            annotations = self._annotate_single_loop(template)
            samples.append({
                'code': template,
                'annotations': annotations,
                'complexity': 'O(n)',
                'primary_drivers': ['single_for_loop']
            })

        return samples

    def _generate_sorting_samples(self, count: int) -> List[Dict[str, Any]]:
        """Generate sorting examples"""
        samples = []
        templates = [
            """def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)""",

            """def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)"""
        ]

        for i, template in enumerate(templates[:count]):
            annotations = self._annotate_sorting(template)
            samples.append({
                'code': template,
                'annotations': annotations,
                'complexity': 'O(n log n)',
                'primary_drivers': ['recursive_calls', 'divide_conquer']
            })

        return samples

    def _generate_search_samples(self, count: int) -> List[Dict[str, Any]]:
        """Generate search algorithm examples"""
        samples = []
        templates = [
            """def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1"""
        ]

        for i, template in enumerate(templates[:count]):
            annotations = self._annotate_search(template)
            samples.append({
                'code': template,
                'annotations': annotations,
                'complexity': 'O(log n)',
                'primary_drivers': ['binary_partition']
            })

        return samples

    def _generate_recursive_samples(self, count: int) -> List[Dict[str, Any]]:
        """Generate recursive examples"""
        samples = []
        templates = [
            """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)""",

            """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)"""
        ]

        for i, template in enumerate(templates[:count]):
            annotations = self._annotate_recursive(template)
            samples.append({
                'code': template,
                'annotations': annotations,
                'complexity': 'Variable',
                'primary_drivers': ['recursive_calls']
            })

        return samples

    def _annotate_nested_loops(self, code: str) -> List[Dict[str, Any]]:
        """Annotate nested loop tokens with high importance"""
        tokens = []
        lines = code.split('\n')

        for line_idx, line in enumerate(lines):
            for token_match in re.finditer(r'\w+', line):
                token = token_match.group()
                importance = 0.1  # Default low importance

                # High importance for loop keywords
                if token in ['for', 'while']:
                    importance = 0.95
                elif token in ['range', 'len']:
                    importance = 0.8
                elif token in ['in', 'if']:
                    importance = 0.7

                tokens.append({
                    'token': token,
                    'line': line_idx,
                    'position': token_match.start(),
                    'importance': importance,
                    'category': self._categorize_token(token)
                })

        return tokens

    def _annotate_single_loop(self, code: str) -> List[Dict[str, Any]]:
        """Annotate single loop tokens"""
        tokens = []
        lines = code.split('\n')

        for line_idx, line in enumerate(lines):
            for token_match in re.finditer(r'\w+', line):
                token = token_match.group()
                importance = 0.1

                if token in ['for', 'while']:
                    importance = 0.8
                elif token in ['range', 'len']:
                    importance = 0.7
                elif token in ['in', 'if']:
                    importance = 0.6

                tokens.append({
                    'token': token,
                    'line': line_idx,
                    'position': token_match.start(),
                    'importance': importance,
                    'category': self._categorize_token(token)
                })

        return tokens

    def _annotate_sorting(self, code: str) -> List[Dict[str, Any]]:
        """Annotate sorting algorithm tokens"""
        tokens = []
        lines = code.split('\n')

        for line_idx, line in enumerate(lines):
            for token_match in re.finditer(r'\w+', line):
                token = token_match.group()
                importance = 0.1

                if token in ['sort', 'merge', 'quick']:
                    importance = 0.9
                elif token in ['left', 'right', 'pivot']:
                    importance = 0.8
                elif token in ['return', 'if']:
                    importance = 0.7

                tokens.append({
                    'token': token,
                    'line': line_idx,
                    'position': token_match.start(),
                    'importance': importance,
                    'category': self._categorize_token(token)
                })

        return tokens

    def _annotate_search(self, code: str) -> List[Dict[str, Any]]:
        """Annotate search algorithm tokens"""
        tokens = []
        lines = code.split('\n')

        for line_idx, line in enumerate(lines):
            for token_match in re.finditer(r'\w+', line):
                token = token_match.group()
                importance = 0.1

                if token in ['binary', 'search']:
                    importance = 0.9
                elif token in ['left', 'right', 'mid']:
                    importance = 0.8
                elif token in ['while', 'if']:
                    importance = 0.7

                tokens.append({
                    'token': token,
                    'line': line_idx,
                    'position': token_match.start(),
                    'importance': importance,
                    'category': self._categorize_token(token)
                })

        return tokens

    def _annotate_recursive(self, code: str) -> List[Dict[str, Any]]:
        """Annotate recursive function tokens"""
        tokens = []
        lines = code.split('\n')

        for line_idx, line in enumerate(lines):
            for token_match in re.finditer(r'\w+', line):
                token = token_match.group()
                importance = 0.1

                if 'return' in line and token in ['fibonacci', 'factorial']:
                    importance = 0.9
                elif token in ['return', 'if']:
                    importance = 0.8
                elif token in ['def', 'n']:
                    importance = 0.6

                tokens.append({
                    'token': token,
                    'line': line_idx,
                    'position': token_match.start(),
                    'importance': importance,
                    'category': self._categorize_token(token)
                })

        return tokens

    def _categorize_token(self, token: str) -> str:
        """Categorize token type for analysis"""
        control_flow = ['for', 'while', 'if', 'else', 'return', 'break', 'continue']
        data_structure = ['list', 'dict', 'set', 'array', 'len', 'range']
        algorithm = ['sort', 'search', 'merge', 'binary', 'quick']

        if token in control_flow:
            return 'control_flow'
        elif token in data_structure:
            return 'data_structure'
        elif token in algorithm:
            return 'algorithm'
        else:
            return 'variable'

class SimpleCausalSalienceModel:
    """
    Simplified causal salience model for the PoC.
    In production, this would be a trained transformer model.
    """

    def __init__(self):
        self.complexity_analyzer = CodeComplexityAnalyzer()
        self.dataset_generator = CausalDatasetGenerator()
        self.trained = False
        self.token_importance_patterns = {}

    def train(self, training_data: List[Dict[str, Any]] = None):
        """Train the model (simplified for PoC)"""
        if training_data is None:
            logging.info("Generating training data...")
            training_data = self.dataset_generator.generate_training_data(2000)

        # Extract patterns from training data
        self._extract_importance_patterns(training_data)
        self.trained = True
        logging.info("Causal salience model training completed")

    def _extract_importance_patterns(self, training_data: List[Dict[str, Any]]):
        """Extract token importance patterns from training data"""
        token_importance_stats = defaultdict(list)

        for sample in training_data:
            annotations = sample['annotations']
            for annotation in annotations:
                token = annotation['token']
                importance = annotation['importance']
                category = annotation['category']

                token_importance_stats[token].append({
                    'importance': importance,
                    'category': category,
                    'complexity': sample['complexity']
                })

        # Calculate average importance for each token
        for token, stats in token_importance_stats.items():
            avg_importance = np.mean([s['importance'] for s in stats])
            most_common_category = Counter([s['category'] for s in stats]).most_common(1)[0][0]

            self.token_importance_patterns[token] = {
                'avg_importance': avg_importance,
                'category': most_common_category,
                'frequency': len(stats)
            }

    def generate_salience_map(self, code: str) -> CausalSalienceMap:
        """Generate causal salience map for given code"""
        if not self.trained:
            self.train()

        # Tokenize code
        tokens = self._tokenize_code(code)

        # Calculate importance scores
        token_importances = []
        for i, token in enumerate(tokens):
            importance_score = self._calculate_token_importance(token, code, i)
            category = self._get_token_category(token)
            explanation = self._generate_explanation(token, importance_score, category)

            token_importances.append(TokenImportance(
                token=token,
                position=i,
                importance_score=importance_score,
                causal_category=category,
                explanation=explanation
            ))

        # Identify overall complexity driver
        complexity_driver = self._identify_complexity_driver(code, token_importances)

        # Calculate confidence
        confidence = self._calculate_confidence(token_importances)

        return CausalSalienceMap(
            code=code,
            token_importances=token_importances,
            overall_complexity_driver=complexity_driver,
            confidence=confidence,
            methodology="simplified_pattern_matching"
        )

    def _tokenize_code(self, code: str) -> List[str]:
        """Tokenize code into meaningful tokens"""
        if TOKENIZE_AVAILABLE:
            tokens = []
            try:
                token_generator = tokenize.generate_tokens(StringIO(code).readline)
                for token in token_generator:
                    if token.type not in [tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL]:
                        tokens.append(token.string)
                return tokens
            except:
                pass

        # Fallback to simple regex tokenization
        return re.findall(r'\w+|[^\w\s]', code)

    def _calculate_token_importance(self, token: str, code: str, position: int) -> float:
        """Calculate importance score for a token"""
        # Use learned patterns if available
        if token in self.token_importance_patterns:
            base_score = self.token_importance_patterns[token]['avg_importance']
        else:
            base_score = 0.1  # Default low importance

        # Contextual adjustments
        context_multiplier = 1.0

        # Higher importance for loop keywords in nested contexts
        if token in ['for', 'while'] and 'for' in code and code.count('for') > 1:
            context_multiplier = 1.2

        # Higher importance for function names that appear in recursive calls
        if token in code and code.count(token) > 1 and 'return' in code:
            context_multiplier = 1.1

        return min(1.0, base_score * context_multiplier)

    def _get_token_category(self, token: str) -> str:
        """Get token category"""
        if token in self.token_importance_patterns:
            return self.token_importance_patterns[token]['category']
        return self.dataset_generator._categorize_token(token)

    def _generate_explanation(self, token: str, importance: float, category: str) -> str:
        """Generate explanation for token importance"""
        if importance > 0.8:
            return f"High causal importance: {token} is a primary {category} driver"
        elif importance > 0.6:
            return f"Moderate causal importance: {token} contributes to {category}"
        else:
            return f"Low causal importance: {token} has minimal algorithmic impact"

    def _identify_complexity_driver(self, code: str, token_importances: List[TokenImportance]) -> str:
        """Identify the primary complexity driver"""
        high_importance_tokens = [t for t in token_importances if t.importance_score > 0.8]

        if any('for' in t.token for t in high_importance_tokens) and code.count('for') > 1:
            return "nested_loops"
        elif any('for' in t.token or 'while' in t.token for t in high_importance_tokens):
            return "single_loop"
        elif 'return' in code and any(t.token in code for t in high_importance_tokens):
            return "recursive_structure"
        else:
            return "linear_operations"

    def _calculate_confidence(self, token_importances: List[TokenImportance]) -> float:
        """Calculate confidence in the salience analysis"""
        high_importance_count = sum(1 for t in token_importances if t.importance_score > 0.7)
        total_tokens = len(token_importances)

        if total_tokens == 0:
            return 0.0

        # Confidence based on presence of clearly important tokens
        confidence = min(0.95, high_importance_count / total_tokens * 2)
        return max(0.1, confidence)

class EnhancedCausalAttentionWrapper:
    """
    Enhanced wrapper that uses the causal salience model.
    Replaces the heuristic-based v0.1 implementation.
    """

    def __init__(self):
        self.salience_model = SimpleCausalSalienceModel()
        self.salience_model.train()  # Train on initialization

    def generate_causal_prompt(self, code: str, task_description: str = "") -> str:
        """Generate causal-focused prompt using salience model"""
        salience_map = self.salience_model.generate_salience_map(code)

        # Get top important tokens
        top_tokens = sorted(
            salience_map.token_importances,
            key=lambda x: x.importance_score,
            reverse=True
        )[:5]

        # Build causal focus instructions
        causal_instructions = []
        for token in top_tokens:
            if token.importance_score > 0.7:
                causal_instructions.append(
                    f"Focus on '{token.token}' (importance: {token.importance_score:.2f}) - {token.explanation}"
                )

        prompt = f"""
{task_description}

CAUSAL ATTENTION ANALYSIS:
Primary complexity driver: {salience_map.overall_complexity_driver}
Confidence: {salience_map.confidence:.2f}

CAUSAL FOCUS POINTS:
{chr(10).join(causal_instructions)}

When refactoring this code, pay special attention to these causally important elements.
The tokens identified above are the primary drivers of algorithmic complexity.
Focus your optimization efforts on these specific constructs.
"""

        return prompt

    def get_salience_map(self, code: str) -> CausalSalienceMap:
        """Get the full salience map for analysis"""
        return self.salience_model.generate_salience_map(code)

    def visualize_salience(self, code: str) -> str:
        """Create visual representation of token importance"""
        salience_map = self.salience_model.generate_salience_map(code)

        # Create simple text visualization
        lines = code.split('\n')
        visualization = []

        for line in lines:
            visual_line = line
            for token in salience_map.token_importances:
                if token.token in line and token.importance_score > 0.6:
                    # Highlight important tokens
                    marker = "***" if token.importance_score > 0.8 else "**"
                    visual_line = visual_line.replace(
                        token.token,
                        f"{marker}{token.token}{marker}"
                    )
            visualization.append(visual_line)

        return '\n'.join(visualization)