import logging
from typing import Dict, Any
from prometheus.llm_provider import LLMProvider
from prometheus.ast_analyzer import ASTComplexityAnalyzer
from schemas.messaging import CausalFocus

logger = logging.getLogger(__name__)

# Import the sophisticated I.J. Good Weight of Evidence implementation
try:
    from causal_attention_enhanced import EnhancedCausalAttentionWrapper
    ENHANCED_CAUSAL_AVAILABLE = True
    logger.info("✅ Enhanced I.J. Good Weight of Evidence Causal Attention loaded")
except ImportError as e:
    ENHANCED_CAUSAL_AVAILABLE = False
    logger.warning(f"⚠️ Enhanced Causal Attention not available: {e}")

class CausalAttentionWrapper:
    """
    Causal Attention Head implementing I.J. Good's Weight of Evidence calculus
    Falls back to simple heuristics if enhanced version unavailable
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        if ENHANCED_CAUSAL_AVAILABLE:
            self.enhanced_wrapper = EnhancedCausalAttentionWrapper(api_key)
            self.mode = "enhanced"
            logger.info("🧠 Using Enhanced Weight of Evidence Causal Attention")
        else:
            self.llm_provider = LLMProvider(api_key)
            self.mode = "basic"
            logger.info("🧠 Using AST-based Causal Attention")

    def _analyze_code_ast(self, code: str) -> Dict[str, Any]:
        """Analyzes code complexity using AST."""
        analyzer = ASTComplexityAnalyzer(code)
        return analyzer.analyze()

    def compare_code(self, original_code: str, refactored_code: str) -> CausalFocus:
        """Compares two pieces of code and returns a causal diff."""
        original_metrics = self._analyze_code_ast(original_code)
        refactored_metrics = self._analyze_code_ast(refactored_code)

        if refactored_metrics["max_loop_depth"] < original_metrics["max_loop_depth"]:
            return CausalFocus(
                change_type="REDUCED_LOOP_DEPTH",
                from_value=original_metrics["max_loop_depth"],
                to_value=refactored_metrics["max_loop_depth"],
            )

        if refactored_metrics["recursion_detected"] and not original_metrics["recursion_detected"]:
            return CausalFocus(
                change_type="ADDED_RECURSION",
                from_value=False,
                to_value=True,
            )

        if not refactored_metrics["recursion_detected"] and original_metrics["recursion_detected"]:
            return CausalFocus(
                change_type="REMOVED_RECURSION",
                from_value=True,
                to_value=False,
            )

        return CausalFocus(
            change_type="NO_CHANGE",
            from_value=original_metrics,
            to_value=refactored_metrics,
        )

    def generate_with_causal_focus(self, original_code: str, instruction: str) -> str:
        """Generate optimized code with causal focus"""

        if self.mode == "enhanced":
            # Use sophisticated I.J. Good Weight of Evidence calculus
            logger.info("🎯 Applying I.J. Good Weight of Evidence Analysis")
            return self.enhanced_wrapper.generate_with_causal_focus(original_code, instruction)

        else:
            # Fall back to AST-based analysis
            logger.info("🎯 Applying AST-based Analysis")
            causal_analysis = self._analyze_code_ast(original_code)

            focus_areas = []
            if causal_analysis["max_loop_depth"] > 1:
                focus_areas.append(f"nested loops (depth {causal_analysis['max_loop_depth']})")
            if causal_analysis["recursion_detected"]:
                focus_areas.append("recursion")

            focus_str = ", ".join(focus_areas) or "general optimization"

            meta_prompt = f"""You are an expert algorithmic optimizer with causal reasoning capabilities.
AST-BASED CAUSAL ANALYSIS RESULTS:
- Max loop nesting depth: {causal_analysis['max_loop_depth']}
- Recursion detected: {causal_analysis['recursion_detected']}
- Primary focus areas: {focus_str}

OPTIMIZATION PRIORITY: Focus on {focus_str} as the primary causal factor.
IGNORE: Variable naming, comments, code style - these are non-causal surface features.
"""

            prompt = f"""{meta_prompt}

Original code:
```python
{original_code}
```

Instruction: {instruction}

Provide ONLY the refactored Python code without explanations or markdown formatting.
"""

            logger.info(f"🧠 AST-based Causal Analysis - Focus: {focus_str}")

            new_code = self.llm_provider.generate_content(prompt)

            # Clean up response
            if new_code.startswith("```python"):
                new_code = new_code[9:]
            if new_code.endswith("```"):
                new_code = new_code[:-3]

            return new_code.strip()

    def get_causal_insights(self, original_code: str) -> str:
        """Get human-readable causal insights"""
        if self.mode == "enhanced":
            return self.enhanced_wrapper.get_causal_insights(original_code)
        else:
            analysis = self._analyze_code_ast(original_code)
            insights = []
            insights.append("🧠 AST-BASED CAUSAL ANALYSIS")
            insights.append("=" * 30)
            insights.append(f"Max loop nesting depth: {analysis['max_loop_depth']}")
            insights.append(f"Recursion detected: {analysis['recursion_detected']}")
            return "\n".join(insights)
