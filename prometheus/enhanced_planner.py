"""
Enhanced Planner Agent with JSON communication protocol and causal focus
Implements features from v0.19 onwards
"""

import google.generativeai as genai
import os
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from .schemas.communication import (
    AgentMessage, MessageType, PlannerToCoderInstruction
)
from .causal_attention import CausalAttentionHead

class EnhancedPlannerAgent:
    """Enhanced Planner Agent with structured communication and causal focus"""

    def __init__(self, api_key: str = None, causal_attention: CausalAttentionHead = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logging.warning("No API key provided - using mock responses")

        self.causal_attention = causal_attention or CausalAttentionHead()
        self.agent_id = "planner_agent"

    def plan_task(self, task_description: str, initial_code: str, run_id: str) -> AgentMessage:
        """Generate a structured plan for a coding task"""

        # Generate causal focus
        causal_focus = self.causal_attention.generate_causal_focus(initial_code, task_description)

        # Analyze performance requirements
        performance_requirements = self._analyze_performance_requirements(task_description, initial_code)

        # Generate meta-prompt for the coder
        meta_prompt = self._generate_meta_prompt(task_description, causal_focus)

        # Create structured instruction
        instruction = PlannerToCoderInstruction(
            task_description=task_description,
            initial_code=initial_code,
            performance_requirements=performance_requirements,
            causal_focus=causal_focus,
            meta_prompt=meta_prompt
        )

        # Create agent message
        message = AgentMessage(
            message_type=MessageType.PLANNER_TO_CODER,
            sender=self.agent_id,
            recipient="coder_agent",
            timestamp=datetime.now().isoformat(),
            run_id=run_id,
            payload=instruction.dict()
        )

        logging.info(f"PlannerAgent generated task plan for run {run_id}")
        return message

    def generate_strategic_plans(self, task_description: str, initial_code: str,
                               num_strategies: int = 3) -> List[Dict[str, Any]]:
        """Generate multiple strategic approaches for solving a task (v0.38+)"""

        if not self.model:
            return self._mock_strategic_plans(task_description, num_strategies)

        prompt = f"""
        You are an expert software architect. Given the following task and code,
        generate {num_strategies} different high-level strategies for optimization.

        Task: {task_description}

        Initial Code:
        ```python
        {initial_code}
        ```

        For each strategy, provide:
        1. A clear name/title
        2. The core approach (2-3 sentences)
        3. Expected time complexity improvement
        4. Expected space complexity impact
        5. Implementation difficulty (1-5 scale)

        Return as JSON array of strategy objects.
        """

        try:
            response = self.model.generate_content(prompt)
            strategies_text = response.text.strip()

            # Try to parse JSON response
            if strategies_text.startswith('['):
                strategies = json.loads(strategies_text)
            else:
                # Fallback parsing
                strategies = self._parse_strategies_fallback(strategies_text, num_strategies)

        except Exception as e:
            logging.error(f"Error generating strategies: {e}")
            strategies = self._mock_strategic_plans(task_description, num_strategies)

        return strategies

    def classify_problem_type(self, task_description: str, code: str) -> str:
        """Classify the type of optimization problem (v0.37+)"""

        # Analyze code characteristics
        code_lower = code.lower()
        task_lower = task_description.lower()

        # Simple classification based on keywords and patterns
        if "nested" in task_lower or code.count("for") > 1:
            return "LOOP_OPTIMIZATION"
        elif "recursive" in task_lower or "recursion" in task_lower:
            return "RECURSION_REFACTOR"
        elif "sort" in task_lower or "search" in task_lower:
            return "DATA_STRUCTURE_SWAP"
        elif "lookup" in task_lower or "find" in task_lower:
            return "SEARCH_OPTIMIZATION"
        else:
            return "GENERAL_OPTIMIZATION"

    def _analyze_performance_requirements(self, task_description: str, code: str) -> Dict[str, Any]:
        """Analyze and extract performance requirements from the task"""

        requirements = {
            "primary_metric": "time_complexity",
            "secondary_metrics": ["space_complexity", "readability"],
            "constraints": [],
            "target_complexity": None
        }

        # Extract requirements from task description
        task_lower = task_description.lower()

        if "o(n)" in task_lower or "linear" in task_lower:
            requirements["target_complexity"] = "O(n)"
        elif "o(log n)" in task_lower or "logarithmic" in task_lower:
            requirements["target_complexity"] = "O(log n)"
        elif "constant" in task_lower or "o(1)" in task_lower:
            requirements["target_complexity"] = "O(1)"

        if "memory" in task_lower or "space" in task_lower:
            requirements["primary_metric"] = "space_complexity"

        if "readable" in task_lower or "maintainable" in task_lower:
            requirements["constraints"].append("maintain_readability")

        return requirements

    def _generate_meta_prompt(self, task_description: str, causal_focus: Dict[str, Any]) -> str:
        """Generate meta-prompt for the coder based on causal analysis"""

        concerns = causal_focus.get("primary_concerns", [])
        targets = causal_focus.get("attention_targets", [])
        hints = causal_focus.get("optimization_hints", [])

        meta_prompt = f"Task: {task_description}\n\n"

        if concerns:
            meta_prompt += f"PRIMARY CONCERNS TO ADDRESS:\n"
            for concern in concerns:
                meta_prompt += f"- {concern.replace('_', ' ').title()}\n"
            meta_prompt += "\n"

        if targets:
            meta_prompt += f"FOCUS YOUR ATTENTION ON:\n"
            for target in targets:
                meta_prompt += f"- {target.replace('_', ' ').title()}\n"
            meta_prompt += "\n"

        if hints:
            meta_prompt += f"OPTIMIZATION HINTS:\n"
            for hint in hints:
                meta_prompt += f"- {hint}\n"
            meta_prompt += "\n"

        meta_prompt += "Please refactor the code to address these specific concerns while maintaining functional correctness."

        return meta_prompt

    def _mock_strategic_plans(self, task_description: str, num_strategies: int) -> List[Dict[str, Any]]:
        """Generate mock strategic plans when LLM is unavailable"""

        strategies = [
            {
                "name": "Hash Map Optimization",
                "approach": "Replace nested loops with hash map lookups for O(1) access time",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)",
                "difficulty": 2
            },
            {
                "name": "Sorting + Binary Search",
                "approach": "Pre-sort data and use binary search for efficient lookups",
                "time_complexity": "O(n log n)",
                "space_complexity": "O(1)",
                "difficulty": 3
            },
            {
                "name": "Dynamic Programming",
                "approach": "Cache intermediate results to avoid redundant computations",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)",
                "difficulty": 4
            }
        ]

        return strategies[:num_strategies]

    def _parse_strategies_fallback(self, text: str, num_strategies: int) -> List[Dict[str, Any]]:
        """Fallback parser for strategy text"""

        # Simple fallback - return mock strategies
        return self._mock_strategic_plans("fallback task", num_strategies)

    def generate_bid(self, goal: str) -> List[Dict[str, Any]]:
        """Legacy method for backward compatibility"""

        # Convert to new format
        strategies = self.generate_strategic_plans(goal, "# placeholder code", 2)

        bids = []
        for i, strategy in enumerate(strategies):
            cost = (strategy.get("difficulty", 3) * 10) + (i * 5)
            bids.append({
                "plan": strategy.get("approach", "Generic optimization plan"),
                "cost": cost,
                "agent": f"strategy_{i+1}",
                "strategy": strategy
            })

        return bids

    def estimate_cost(self, plan: str) -> int:
        """Legacy method for backward compatibility"""
        return len(plan.split()) * 10