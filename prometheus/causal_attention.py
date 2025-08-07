import logging
import google.generativeai as genai
from typing import Dict, Any

# Import the sophisticated I.J. Good Weight of Evidence implementation
try:
    from causal_attention_enhanced import EnhancedCausalAttentionWrapper
    ENHANCED_CAUSAL_AVAILABLE = True
    logging.info("✅ Enhanced I.J. Good Weight of Evidence Causal Attention loaded")
except ImportError as e:
    ENHANCED_CAUSAL_AVAILABLE = False
    logging.warning(f"⚠️ Enhanced Causal Attention not available: {e}")


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
            logging.info("🧠 Using Enhanced Weight of Evidence Causal Attention")
        else:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.mode = "basic"
            logging.info("🧠 Using Basic Heuristic Causal Attention")

    def _analyze_code_basic(self, code: str) -> Dict[str, Any]:
        """Basic heuristic analysis as fallback"""
        lines = code.strip().split('\n')
        analysis = {
            'complexity_issues': [],
            'causal_features': [],
            'optimization_targets': []
        }

        indentation_levels = [len(line) - len(line.lstrip(' ')) for line in lines]

        # Basic nested loop detection
        for i in range(len(lines)):
            line_i = lines[i].strip()
            if line_i.startswith("for ") or line_i.startswith("while "):
                for j in range(i + 1, len(lines)):
                    line_j = lines[j].strip()
                    if ((line_j.startswith("for ") or line_j.startswith("while ")) and
                        indentation_levels[j] > indentation_levels[i]):
                        analysis['complexity_issues'].append("O(n^2) complexity due to nested loops")
                        analysis['causal_features'].append("nested_loops")
                        analysis['optimization_targets'].append("algorithmic_efficiency")
                        break

        # Basic recursion detection
        for line in lines:
            if "def " in line:
                function_name = line.split("def ")[1].split("(")[0]
                if f" {function_name}(" in code and not f"def {function_name}(" in line:
                    analysis['complexity_issues'].append("Potential recursion detected")
                    analysis['causal_features'].append("recursion")
                    analysis['optimization_targets'].append("tail_recursion_or_iteration")

        if not analysis['complexity_issues']:
            analysis['complexity_issues'].append("No obvious algorithmic inefficiencies detected")

        return analysis

    def generate_with_causal_focus(self, original_code: str, instruction: str) -> str:
        """Generate optimized code with causal focus"""

        if self.mode == "enhanced":
            # Use sophisticated I.J. Good Weight of Evidence calculus
            logging.info("🎯 Applying I.J. Good Weight of Evidence Analysis")
            return self.enhanced_wrapper.generate_with_causal_focus(original_code, instruction)

        else:
            # Fall back to basic heuristic analysis
            logging.info("🎯 Applying Basic Heuristic Analysis")
            causal_analysis = self._analyze_code_basic(original_code)

            evidence_weight = len(causal_analysis['complexity_issues'])
            focus_areas = ", ".join(causal_analysis['optimization_targets']) or "general optimization"

            meta_prompt = f"""You are an expert algorithmic optimizer with causal reasoning capabilities.
BASIC CAUSAL ANALYSIS RESULTS:
- Issues detected: {', '.join(causal_analysis['complexity_issues'])}
- Causal features: {', '.join(causal_analysis['causal_features'])}
- Primary focus areas: {focus_areas}
- Evidence weight: {evidence_weight}/10

OPTIMIZATION PRIORITY: Focus on {focus_areas} as the primary causal factor.
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

            logging.info(f"🧠 Basic Causal Analysis - Focus: {focus_areas}")

            response = self.model.generate_content(prompt)
            new_code = response.text.strip()

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
            analysis = self._analyze_code_basic(original_code)
            insights = []
            insights.append("🧠 BASIC CAUSAL ANALYSIS")
            insights.append("=" * 30)
            insights.append(f"Issues: {', '.join(analysis['complexity_issues'])}")
            insights.append(f"Features: {', '.join(analysis['causal_features'])}")
            insights.append(f"Targets: {', '.join(analysis['optimization_targets'])}")
            return "\n".join(insights)
