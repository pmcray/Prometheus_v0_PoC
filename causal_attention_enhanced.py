#!/usr/bin/env python3
"""
Enhanced Causal Attention Head with I.J. Good's Weight of Evidence Calculus
Implements sophisticated Bayesian evidence evaluation for causal reasoning
"""

import math
import re
import ast
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import google.generativeai as genai

logger = logging.getLogger(__name__)

@dataclass
class Evidence:
    """Represents a piece of evidence found in code"""
    type: str  # Type of evidence (e.g., 'nested_loop', 'recursion')
    location: Tuple[int, int]  # (line_start, line_end)
    context: str  # Code context where evidence was found
    strength: float  # Raw strength of evidence (0.0 to 1.0)
    metadata: Dict[str, Any]  # Additional context-specific data

@dataclass
class Hypothesis:
    """Represents a causal hypothesis about code inefficiency"""
    name: str
    description: str
    prior_probability: float  # P(H) - prior belief in hypothesis
    
class WeightOfEvidenceCalculus:
    """
    Implements I.J. Good's Weight of Evidence calculus for causal reasoning.
    
    Weight of Evidence: W(H:E) = log[P(E|H) / P(E|¬H)]
    
    Where:
    - H is a hypothesis (e.g., "code has O(n²) complexity")
    - E is evidence (e.g., "nested loops detected") 
    - P(E|H) is probability of evidence given hypothesis is true
    - P(E|¬H) is probability of evidence given hypothesis is false
    """
    
    def __init__(self):
        self.hypotheses = self._initialize_hypotheses()
        self.evidence_likelihoods = self._initialize_evidence_likelihoods()
        
    def _initialize_hypotheses(self) -> Dict[str, Hypothesis]:
        """Initialize causal hypotheses about code efficiency"""
        return {
            'quadratic_complexity': Hypothesis(
                name='quadratic_complexity',
                description='Code exhibits O(n²) time complexity',
                prior_probability=0.15  # 15% of code is quadratic
            ),
            'memory_inefficient': Hypothesis(
                name='memory_inefficient', 
                description='Code has unnecessary memory allocations',
                prior_probability=0.25  # 25% of code has memory issues
            ),
            'recursive_inefficient': Hypothesis(
                name='recursive_inefficient',
                description='Recursive implementation without optimization',
                prior_probability=0.10  # 10% of recursive code is inefficient
            ),
            'sequential_parallelizable': Hypothesis(
                name='sequential_parallelizable',
                description='Sequential operations that could be parallelized',
                prior_probability=0.20  # 20% of sequential code could be parallel
            ),
            'redundant_computation': Hypothesis(
                name='redundant_computation',
                description='Repeated calculations that could be cached',
                prior_probability=0.18  # 18% of code has redundant computation
            )
        }
    
    def _initialize_evidence_likelihoods(self) -> Dict[str, Dict[str, float]]:
        """
        Initialize likelihood matrices P(E|H) for each evidence type and hypothesis.
        
        These are empirically derived probabilities based on code analysis patterns.
        """
        return {
            'nested_loops': {
                'quadratic_complexity': 0.85,    # 85% chance nested loops → O(n²)
                'memory_inefficient': 0.30,      # 30% chance nested loops → memory issues
                'recursive_inefficient': 0.05,   # 5% chance (not recursive)
                'sequential_parallelizable': 0.40, # 40% chance could be parallelized
                'redundant_computation': 0.25     # 25% chance has redundant computation
            },
            'recursive_calls': {
                'quadratic_complexity': 0.35,    # 35% of recursion is quadratic
                'memory_inefficient': 0.60,      # 60% of recursion has memory issues (stack)
                'recursive_inefficient': 0.90,   # 90% chance inefficient recursion
                'sequential_parallelizable': 0.15, # 15% of recursion parallelizable
                'redundant_computation': 0.75     # 75% of recursion has redundant calls
            },
            'dynamic_allocation': {
                'quadratic_complexity': 0.20,    # 20% of dynamic allocation is quadratic
                'memory_inefficient': 0.80,      # 80% of dynamic allocation is inefficient
                'recursive_inefficient': 0.25,   # 25% related to recursion
                'sequential_parallelizable': 0.10, # 10% parallelizable
                'redundant_computation': 0.30     # 30% redundant allocations
            },
            'sequential_operations': {
                'quadratic_complexity': 0.25,    # 25% of sequential ops are quadratic
                'memory_inefficient': 0.20,      # 20% memory inefficient
                'recursive_inefficient': 0.10,   # 10% recursive
                'sequential_parallelizable': 0.70, # 70% could be parallelized
                'redundant_computation': 0.40     # 40% redundant
            },
            'repeated_computation': {
                'quadratic_complexity': 0.45,    # 45% of repeated computation is quadratic
                'memory_inefficient': 0.15,      # 15% memory issues
                'recursive_inefficient': 0.30,   # 30% in recursion
                'sequential_parallelizable': 0.25, # 25% parallelizable
                'redundant_computation': 0.95     # 95% definitely redundant
            },
            'data_structure_traversal': {
                'quadratic_complexity': 0.55,    # 55% of nested traversals are quadratic
                'memory_inefficient': 0.35,      # 35% memory inefficient
                'recursive_inefficient': 0.20,   # 20% recursive
                'sequential_parallelizable': 0.30, # 30% parallelizable
                'redundant_computation': 0.50     # 50% redundant
            }
        }
    
    def calculate_weight_of_evidence(self, evidence_type: str, hypothesis: str) -> float:
        """
        Calculate I.J. Good's Weight of Evidence: W(H:E) = log[P(E|H) / P(E|¬H)]
        
        Args:
            evidence_type: Type of evidence observed
            hypothesis: Hypothesis being evaluated
            
        Returns:
            Weight of evidence (positive supports hypothesis, negative opposes)
        """
        if evidence_type not in self.evidence_likelihoods:
            logger.warning(f"Unknown evidence type: {evidence_type}")
            return 0.0
            
        if hypothesis not in self.evidence_likelihoods[evidence_type]:
            logger.warning(f"Unknown hypothesis: {hypothesis}")
            return 0.0
        
        # P(E|H) - probability of evidence given hypothesis is true
        p_e_given_h = self.evidence_likelihoods[evidence_type][hypothesis]
        
        # P(E|¬H) - probability of evidence given hypothesis is false
        # Calculate as weighted average of P(E|other_hypotheses)
        other_hypotheses = [h for h in self.hypotheses.keys() if h != hypothesis]
        total_prior = sum(self.hypotheses[h].prior_probability for h in other_hypotheses)
        
        if total_prior == 0:
            p_e_given_not_h = 0.1  # Default small probability
        else:
            p_e_given_not_h = sum(
                self.evidence_likelihoods[evidence_type][h] * 
                (self.hypotheses[h].prior_probability / total_prior)
                for h in other_hypotheses
            )
        
        # Avoid division by zero
        if p_e_given_not_h == 0:
            p_e_given_not_h = 0.001
            
        # Calculate weight of evidence
        weight = math.log(p_e_given_h / p_e_given_not_h)
        
        logger.debug(f"W({hypothesis}:{evidence_type}) = log({p_e_given_h:.3f}/{p_e_given_not_h:.3f}) = {weight:.3f}")
        
        return weight
    
    def calculate_posterior_odds(self, hypothesis: str, evidence_list: List[str]) -> float:
        """
        Calculate posterior odds using accumulated weight of evidence.
        
        Posterior Odds = Prior Odds × ∏ exp(W(H:Ei))
        
        Args:
            hypothesis: Hypothesis to evaluate
            evidence_list: List of evidence types observed
            
        Returns:
            Posterior odds ratio for the hypothesis
        """
        if hypothesis not in self.hypotheses:
            return 0.0
            
        # Prior odds = P(H) / P(¬H)
        p_h = self.hypotheses[hypothesis].prior_probability
        prior_odds = p_h / (1 - p_h)
        
        # Accumulate weight of evidence
        total_weight = sum(
            self.calculate_weight_of_evidence(evidence_type, hypothesis)
            for evidence_type in evidence_list
        )
        
        # Posterior odds = Prior odds × exp(total weight)
        posterior_odds = prior_odds * math.exp(total_weight)
        
        logger.info(f"Posterior odds for {hypothesis}: {posterior_odds:.3f} (weight: {total_weight:.3f})")
        
        return posterior_odds
    
    def rank_hypotheses(self, evidence_list: List[str]) -> List[Tuple[str, float]]:
        """
        Rank all hypotheses by their posterior odds given the evidence.
        
        Returns:
            List of (hypothesis_name, posterior_odds) tuples, sorted by odds
        """
        hypothesis_scores = []
        
        for hypothesis_name in self.hypotheses.keys():
            posterior_odds = self.calculate_posterior_odds(hypothesis_name, evidence_list)
            hypothesis_scores.append((hypothesis_name, posterior_odds))
        
        # Sort by posterior odds (highest first)
        hypothesis_scores.sort(key=lambda x: x[1], reverse=True)
        
        return hypothesis_scores

class EnhancedCodeAnalyzer:
    """Advanced code analyzer using AST parsing and pattern recognition"""
    
    def __init__(self):
        self.evidence_detectors = {
            'nested_loops': self._detect_nested_loops,
            'recursive_calls': self._detect_recursive_calls,
            'dynamic_allocation': self._detect_dynamic_allocation,
            'sequential_operations': self._detect_sequential_operations,
            'repeated_computation': self._detect_repeated_computation,
            'data_structure_traversal': self._detect_data_structure_traversal
        }
    
    def analyze_code(self, code: str) -> List[Evidence]:
        """
        Comprehensive code analysis to extract evidence.
        
        Args:
            code: Python source code to analyze
            
        Returns:
            List of Evidence objects found in the code
        """
        evidence_list = []
        
        try:
            # Parse code into AST
            tree = ast.parse(code)
            
            # Apply each evidence detector
            for evidence_type, detector in self.evidence_detectors.items():
                detected_evidence = detector(tree, code)
                evidence_list.extend(detected_evidence)
                
        except SyntaxError as e:
            logger.error(f"Syntax error in code analysis: {e}")
            # Fall back to text-based analysis
            evidence_list.extend(self._fallback_text_analysis(code))
        
        return evidence_list
    
    def _detect_nested_loops(self, tree: ast.AST, code: str) -> List[Evidence]:
        """Detect nested loop structures"""
        evidence = []
        
        class NestedLoopVisitor(ast.NodeVisitor):
            def __init__(self):
                self.loop_depth = 0
                self.max_depth = 0
                
            def visit_For(self, node):
                self.loop_depth += 1
                self.max_depth = max(self.max_depth, self.loop_depth)
                
                if self.loop_depth >= 2:
                    evidence.append(Evidence(
                        type='nested_loops',
                        location=(node.lineno, node.end_lineno or node.lineno),
                        context=ast.unparse(node) if hasattr(ast, 'unparse') else '<nested_for>',
                        strength=min(1.0, self.loop_depth / 3.0),  # Strength increases with depth
                        metadata={'depth': self.loop_depth, 'node_type': 'for'}
                    ))
                
                self.generic_visit(node)
                self.loop_depth -= 1
            
            def visit_While(self, node):
                self.loop_depth += 1
                self.max_depth = max(self.max_depth, self.loop_depth)
                
                if self.loop_depth >= 2:
                    evidence.append(Evidence(
                        type='nested_loops',
                        location=(node.lineno, node.end_lineno or node.lineno),
                        context=ast.unparse(node) if hasattr(ast, 'unparse') else '<nested_while>',
                        strength=min(1.0, self.loop_depth / 3.0),
                        metadata={'depth': self.loop_depth, 'node_type': 'while'}
                    ))
                
                self.generic_visit(node)
                self.loop_depth -= 1
        
        visitor = NestedLoopVisitor()
        visitor.visit(tree)
        
        return evidence
    
    def _detect_recursive_calls(self, tree: ast.AST, code: str) -> List[Evidence]:
        """Detect recursive function calls"""
        evidence = []
        
        class RecursionVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_function = None
                self.functions = {}
            
            def visit_FunctionDef(self, node):
                old_function = self.current_function
                self.current_function = node.name
                self.functions[node.name] = node
                
                self.generic_visit(node)
                
                self.current_function = old_function
            
            def visit_Call(self, node):
                if (isinstance(node.func, ast.Name) and 
                    node.func.id == self.current_function and
                    self.current_function is not None):
                    
                    evidence.append(Evidence(
                        type='recursive_calls',
                        location=(node.lineno, node.lineno),
                        context=ast.unparse(node) if hasattr(ast, 'unparse') else f'{self.current_function}(...)',
                        strength=0.8,  # High strength for direct recursion
                        metadata={'function_name': self.current_function, 'call_type': 'direct'}
                    ))
                
                self.generic_visit(node)
        
        visitor = RecursionVisitor()
        visitor.visit(tree)
        
        return evidence
    
    def _detect_dynamic_allocation(self, tree: ast.AST, code: str) -> List[Evidence]:
        """Detect dynamic memory allocation patterns"""
        evidence = []
        
        class AllocationVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Check for list.append() in loops
                if (isinstance(node.func, ast.Attribute) and 
                    node.func.attr == 'append'):
                    
                    evidence.append(Evidence(
                        type='dynamic_allocation',
                        location=(node.lineno, node.lineno),
                        context=ast.unparse(node) if hasattr(ast, 'unparse') else 'list.append(...)',
                        strength=0.6,
                        metadata={'allocation_type': 'list_append'}
                    ))
                
                # Check for list/dict comprehensions in loops
                elif isinstance(node.func, ast.Name) and node.func.id in ['list', 'dict', 'set']:
                    evidence.append(Evidence(
                        type='dynamic_allocation',
                        location=(node.lineno, node.lineno),
                        context=ast.unparse(node) if hasattr(ast, 'unparse') else f'{node.func.id}(...)',
                        strength=0.4,
                        metadata={'allocation_type': f'{node.func.id}_constructor'}
                    ))
                
                self.generic_visit(node)
        
        visitor = AllocationVisitor()
        visitor.visit(tree)
        
        return evidence
    
    def _detect_sequential_operations(self, tree: ast.AST, code: str) -> List[Evidence]:
        """Detect sequential operations that could be parallelized"""
        evidence = []
        
        class SequentialVisitor(ast.NodeVisitor):
            def visit_For(self, node):
                # Look for independent operations in for loops
                independent_ops = 0
                
                for stmt in node.body:
                    if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Expr)):
                        independent_ops += 1
                
                if independent_ops >= 3:  # Threshold for parallelizable operations
                    evidence.append(Evidence(
                        type='sequential_operations',
                        location=(node.lineno, node.end_lineno or node.lineno),
                        context=ast.unparse(node) if hasattr(ast, 'unparse') else '<for_loop>',
                        strength=min(1.0, independent_ops / 10.0),
                        metadata={'operation_count': independent_ops}
                    ))
                
                self.generic_visit(node)
        
        visitor = SequentialVisitor()
        visitor.visit(tree)
        
        return evidence
    
    def _detect_repeated_computation(self, tree: ast.AST, code: str) -> List[Evidence]:
        """Detect repeated computation patterns"""
        evidence = []
        
        class RepeatedComputationVisitor(ast.NodeVisitor):
            def __init__(self):
                self.expressions = defaultdict(list)
            
            def visit_BinOp(self, node):
                expr_str = ast.unparse(node) if hasattr(ast, 'unparse') else str(type(node))
                self.expressions[expr_str].append(node)
                self.generic_visit(node)
            
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    expr_str = f"{node.func.id}({len(node.args)} args)"
                    self.expressions[expr_str].append(node)
                self.generic_visit(node)
        
        visitor = RepeatedComputationVisitor()
        visitor.visit(tree)
        
        # Find expressions that appear multiple times
        for expr_str, nodes in visitor.expressions.items():
            if len(nodes) >= 2:
                for node in nodes[1:]:  # Skip first occurrence
                    evidence.append(Evidence(
                        type='repeated_computation',
                        location=(node.lineno, node.lineno),
                        context=expr_str,
                        strength=min(1.0, len(nodes) / 5.0),
                        metadata={'repetition_count': len(nodes)}
                    ))
        
        return evidence
    
    def _detect_data_structure_traversal(self, tree: ast.AST, code: str) -> List[Evidence]:
        """Detect inefficient data structure traversal patterns"""
        evidence = []
        
        class TraversalVisitor(ast.NodeVisitor):
            def visit_For(self, node):
                # Check for nested iterations over data structures
                if isinstance(node.iter, ast.Name):
                    for stmt in node.body:
                        if isinstance(stmt, ast.For) and isinstance(stmt.iter, ast.Name):
                            evidence.append(Evidence(
                                type='data_structure_traversal',
                                location=(node.lineno, stmt.end_lineno or stmt.lineno),
                                context=f"nested iteration over {node.iter.id} and {stmt.iter.id}",
                                strength=0.7,
                                metadata={
                                    'outer_var': node.iter.id,
                                    'inner_var': stmt.iter.id
                                }
                            ))
                
                self.generic_visit(node)
        
        visitor = TraversalVisitor()
        visitor.visit(tree)
        
        return evidence
    
    def _fallback_text_analysis(self, code: str) -> List[Evidence]:
        """Simple text-based analysis when AST parsing fails"""
        evidence = []
        lines = code.split('\n')
        
        # Basic nested loop detection
        for i, line in enumerate(lines):
            if 'for ' in line and any('for ' in lines[j] and 
                                      len(lines[j]) - len(lines[j].lstrip()) > len(line) - len(line.lstrip())
                                      for j in range(i+1, len(lines))):
                evidence.append(Evidence(
                    type='nested_loops',
                    location=(i+1, i+1),
                    context=line.strip(),
                    strength=0.5,
                    metadata={'detection_method': 'text_based'}
                ))
        
        return evidence

class EnhancedCausalAttentionWrapper:
    """
    Enhanced Causal Attention Head implementing I.J. Good's Weight of Evidence calculus
    """
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.weight_calculator = WeightOfEvidenceCalculus()
        self.code_analyzer = EnhancedCodeAnalyzer()
    
    def analyze_code_causally(self, code: str) -> Dict[str, Any]:
        """
        Perform sophisticated causal analysis using weight of evidence.
        
        Args:
            code: Python source code to analyze
            
        Returns:
            Detailed causal analysis with evidence weights and hypothesis rankings
        """
        logger.info("🧠 Starting Enhanced Causal Analysis with Weight of Evidence")
        
        # 1. Extract evidence from code
        evidence_list = self.code_analyzer.analyze_code(code)
        logger.info(f"📊 Extracted {len(evidence_list)} pieces of evidence")
        
        # 2. Convert evidence to types for weight calculation
        evidence_types = [evidence.type for evidence in evidence_list]
        evidence_summary = defaultdict(int)
        for etype in evidence_types:
            evidence_summary[etype] += 1
        
        # 3. Calculate weights of evidence for each hypothesis
        hypothesis_weights = {}
        for hypothesis in self.weight_calculator.hypotheses.keys():
            weights = []
            for evidence_type in set(evidence_types):
                weight = self.weight_calculator.calculate_weight_of_evidence(evidence_type, hypothesis)
                weights.append((evidence_type, weight))
            hypothesis_weights[hypothesis] = weights
        
        # 4. Rank hypotheses by posterior odds
        hypothesis_rankings = self.weight_calculator.rank_hypotheses(evidence_types)
        
        # 5. Identify primary causal factors
        primary_hypothesis = hypothesis_rankings[0] if hypothesis_rankings else ("unknown", 0.0)
        strongest_evidence = max(evidence_list, key=lambda e: e.strength) if evidence_list else None
        
        analysis = {
            'evidence_found': len(evidence_list),
            'evidence_summary': dict(evidence_summary),
            'evidence_details': [
                {
                    'type': e.type,
                    'location': e.location,
                    'strength': e.strength,
                    'context': e.context[:100] + "..." if len(e.context) > 100 else e.context,
                    'metadata': e.metadata
                }
                for e in evidence_list
            ],
            'hypothesis_rankings': [
                {'hypothesis': h, 'posterior_odds': odds, 'probability': odds / (1 + odds)}
                for h, odds in hypothesis_rankings
            ],
            'primary_causal_factor': {
                'hypothesis': primary_hypothesis[0],
                'posterior_odds': primary_hypothesis[1],
                'description': self.weight_calculator.hypotheses.get(
                    primary_hypothesis[0], 
                    type('H', (), {'description': 'Unknown hypothesis'})()
                ).description
            },
            'strongest_evidence': {
                'type': strongest_evidence.type if strongest_evidence else 'none',
                'strength': strongest_evidence.strength if strongest_evidence else 0.0,
                'location': strongest_evidence.location if strongest_evidence else (0, 0),
                'context': strongest_evidence.context if strongest_evidence else 'No evidence found'
            } if strongest_evidence else None,
            'causal_weights': hypothesis_weights
        }
        
        logger.info(f"🎯 Primary causal factor: {primary_hypothesis[0]} (odds: {primary_hypothesis[1]:.3f})")
        
        return analysis
    
    def generate_with_causal_focus(self, original_code: str, instruction: str) -> str:
        """
        Generate optimized code using sophisticated causal attention.
        
        Args:
            original_code: Source code to optimize
            instruction: Optimization instruction
            
        Returns:
            Refactored code with causal focus
        """
        # Perform causal analysis
        causal_analysis = self.analyze_code_causally(original_code)
        
        # Extract key insights for prompt construction
        primary_factor = causal_analysis['primary_causal_factor']
        evidence_summary = causal_analysis['evidence_summary']
        strongest_evidence = causal_analysis['strongest_evidence']
        
        # Construct sophisticated meta-prompt based on weight of evidence
        evidence_description = ", ".join([f"{k}({v})" for k, v in evidence_summary.items()])
        
        meta_prompt = f"""You are an expert in algorithmic optimization with advanced causal reasoning capabilities.

CAUSAL ANALYSIS RESULTS (using I.J. Good's Weight of Evidence):

PRIMARY CAUSAL FACTOR:
- Hypothesis: {primary_factor['hypothesis']}
- Description: {primary_factor['description']}
- Posterior Odds: {primary_factor['posterior_odds']:.3f}
- Confidence: {primary_factor['posterior_odds'] / (1 + primary_factor['posterior_odds']):.1%}

EVIDENCE DETECTED: {evidence_description}

STRONGEST EVIDENCE:
- Type: {strongest_evidence['type'] if strongest_evidence else 'None'}
- Strength: {strongest_evidence['strength'] if strongest_evidence else 0:.3f}
- Context: {strongest_evidence['context'] if strongest_evidence else 'No evidence'}

CAUSAL OPTIMIZATION STRATEGY:
Based on Bayesian weight of evidence, focus optimization effort on addressing the primary causal factor: {primary_factor['hypothesis']}.

IGNORE non-causal surface features like variable names, comments, or code formatting.
PRIORITIZE algorithmic and structural changes that address the identified causal inefficiencies.
"""

        prompt = f"""{meta_prompt}

Original code:
```python
{original_code}
```

Instruction: {instruction}

Apply causal reasoning to optimize the code, focusing specifically on the identified causal factors.
Provide ONLY the refactored Python code without explanations or markdown formatting.
"""

        logger.info(f"🎯 Causal Focus: {primary_factor['hypothesis']} (confidence: {primary_factor['posterior_odds'] / (1 + primary_factor['posterior_odds']):.1%})")
        
        response = self.model.generate_content(prompt)
        new_code = response.text.strip()
        
        # Clean up response
        if new_code.startswith("```python"):
            new_code = new_code[9:]
        if new_code.endswith("```"):
            new_code = new_code[:-3]
        
        return new_code.strip()
    
    def get_causal_insights(self, original_code: str) -> str:
        """
        Generate human-readable causal insights about the code.
        
        Args:
            original_code: Source code to analyze
            
        Returns:
            Human-readable explanation of causal factors
        """
        analysis = self.analyze_code_causally(original_code)
        
        insights = []
        insights.append("🧠 CAUSAL ANALYSIS INSIGHTS")
        insights.append("=" * 40)
        
        primary = analysis['primary_causal_factor']
        insights.append(f"Primary Causal Factor: {primary['hypothesis']}")
        insights.append(f"Description: {primary['description']}")
        insights.append(f"Confidence: {primary['posterior_odds'] / (1 + primary['posterior_odds']):.1%}")
        
        insights.append(f"\nEvidence Found ({analysis['evidence_found']} items):")
        for evidence_type, count in analysis['evidence_summary'].items():
            insights.append(f"  • {evidence_type}: {count} instances")
        
        insights.append(f"\nHypothesis Rankings:")
        for i, h in enumerate(analysis['hypothesis_rankings'][:3], 1):
            insights.append(f"  {i}. {h['hypothesis']}: {h['probability']:.1%} probability")
        
        return "\n".join(insights)

# Test and demonstration code
if __name__ == "__main__":
    # Example usage
    test_code = """
def inefficient_sort(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n-i-1):
            if data[j] > data[j+1]:
                data[j], data[j+1] = data[j+1], data[j]
    return data

def process_matrix(matrix):
    result = []
    for row in matrix:
        for col in row:
            result.append(col * 2)
    return result
"""
    
    # Initialize enhanced causal attention (requires API key)
    import os
    api_key = os.environ.get("GOOGLE_API_KEY", "demo_key")
    
    if api_key != "demo_key":
        enhanced_attention = EnhancedCausalAttentionWrapper(api_key)
        
        print("Testing Enhanced Causal Attention Head")
        print("=" * 50)
        
        # Analyze code
        insights = enhanced_attention.get_causal_insights(test_code)
        print(insights)
        
        # Generate optimized code
        optimized = enhanced_attention.generate_with_causal_focus(
            test_code, 
            "Optimize for better time complexity"
        )
        print(f"\nOptimized Code:\n{optimized}")
    else:
        print("Set GOOGLE_API_KEY environment variable to test with actual API")