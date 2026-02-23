"""
GeneralistPlannerAgent v0.1
Top-level strategic director that translates user goals into self-improvement directives

This agent replaces the CurriculumAgent as the primary initiator of the RSI loop.
It decomposes high-level goals into meta-tasks for the SMM to execute.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class TaskType(Enum):
    """Types of meta-tasks the planner can generate"""
    EVOLVE_AGENT = "evolve_agent"
    OPTIMIZE_CODE = "optimize_code"
    LEARN_SKILL = "learn_skill"
    SYNTHESIZE_TOOL = "synthesize_tool"
    GENERATE_CONTENT = "generate_content"
    SOLVE_PROBLEM = "solve_problem"


@dataclass
class MetaTask:
    """A meta-task directive for the SMM"""
    task_id: str
    task_type: TaskType
    goal: str
    target_benchmark: str
    target_fitness: float
    evolutionary_parameters: Dict[str, Any]
    time_budget: Optional[int]
    created_timestamp: str


@dataclass
class DomainAnalysis:
    """Analysis of a problem domain"""
    domain_name: str
    relevant_benchmarks: List[str]
    suggested_approach: str
    estimated_difficulty: float
    required_capabilities: List[str]


class GeneralistPlannerAgent:
    """
    Top-level strategic planner for generalized capability acquisition

    This agent:
    1. Analyzes high-level user goals
    2. Identifies relevant benchmarks
    3. Decomposes goals into meta-tasks for the SMM
    4. Monitors progress and adjusts strategy
    """

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm and GENAI_AVAILABLE

        if self.use_llm:
            try:
                genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
                self.model = genai.GenerativeModel('generic-cloud-fm')
                logging.info("GeneralistPlannerAgent initialized with LLM support")
            except Exception as e:
                logging.warning(f"LLM initialization failed: {e}. Falling back to rule-based planning.")
                self.use_llm = False

        # Knowledge base of domain-benchmark mappings
        self.domain_knowledge = {
            "draughts": {
                "benchmark": "GGP-draughts",
                "domain": "general_game_playing",
                "approach": "evolutionary_game_agent",
                "difficulty": 0.6
            },
            "checkers": {
                "benchmark": "GGP-draughts",
                "domain": "general_game_playing",
                "approach": "evolutionary_game_agent",
                "difficulty": 0.6
            },
            "chess": {
                "benchmark": "GGP-chess",
                "domain": "general_game_playing",
                "approach": "evolutionary_game_agent",
                "difficulty": 0.8
            },
            "conversation": {
                "benchmark": "ConversationalAI-General",
                "domain": "conversational_ai",
                "approach": "evolutionary_chatbot",
                "difficulty": 0.5
            },
            "chatbot": {
                "benchmark": "ConversationalAI-General",
                "domain": "conversational_ai",
                "approach": "evolutionary_chatbot",
                "difficulty": 0.5
            },
            "code": {
                "benchmark": "Prometheus-Bench-v0.1",
                "domain": "code_optimization",
                "approach": "self_modification",
                "difficulty": 0.7
            }
        }

        self.task_history: List[MetaTask] = []
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def analyze_goal(self, user_goal: str) -> DomainAnalysis:
        """
        Analyze a user goal and identify the relevant domain

        Args:
            user_goal: High-level user goal (e.g., "Master chess", "Become a chatbot")

        Returns:
            Domain analysis with benchmark recommendations
        """
        self.logger.info(f"🎯 Analyzing goal: '{user_goal}'")

        # Extract keywords
        goal_lower = user_goal.lower()

        # Rule-based domain identification
        identified_domains = []

        for keyword, domain_info in self.domain_knowledge.items():
            if keyword in goal_lower:
                identified_domains.append((keyword, domain_info))

        if not identified_domains:
            # Default to code optimization if no match
            self.logger.warning(f"No domain match found for '{user_goal}'. Defaulting to code optimization.")
            identified_domains = [("code", self.domain_knowledge["code"])]

        # Use first match (could be enhanced with LLM for disambiguation)
        keyword, domain_info = identified_domains[0]

        analysis = DomainAnalysis(
            domain_name=domain_info["domain"],
            relevant_benchmarks=[domain_info["benchmark"]],
            suggested_approach=domain_info["approach"],
            estimated_difficulty=domain_info["difficulty"],
            required_capabilities=self._infer_capabilities(domain_info["domain"])
        )

        self.logger.info(f"✓ Domain identified: {analysis.domain_name}")
        self.logger.info(f"  Benchmark: {analysis.relevant_benchmarks[0]}")
        self.logger.info(f"  Approach: {analysis.suggested_approach}")

        return analysis

    def _infer_capabilities(self, domain: str) -> List[str]:
        """Infer required capabilities for a domain"""
        capability_map = {
            "general_game_playing": ["search", "evaluation", "strategic_planning"],
            "conversational_ai": ["natural_language_understanding", "dialogue_management", "response_generation"],
            "code_optimization": ["code_analysis", "refactoring", "performance_tuning"],
            "multimodal_generation": ["image_generation", "audio_synthesis", "cross_modal_reasoning"],
            "mathematical_reasoning": ["symbolic_manipulation", "proof_search", "equation_solving"]
        }

        return capability_map.get(domain, ["general_problem_solving"])

    def create_meta_task(self,
                        user_goal: str,
                        target_fitness: float = 0.8,
                        time_budget: Optional[int] = None) -> MetaTask:
        """
        Create a meta-task directive for the SMM

        Args:
            user_goal: High-level user goal
            target_fitness: Target fitness score to achieve
            time_budget: Optional time budget in seconds

        Returns:
            MetaTask directive
        """
        self.logger.info(f"📝 Creating meta-task for goal: '{user_goal}'")

        # Analyze the goal
        analysis = self.analyze_goal(user_goal)

        # Generate task ID
        task_id = f"meta_task_{len(self.task_history):04d}_{int(datetime.now().timestamp())}"

        # Determine task type based on approach
        task_type_map = {
            "evolutionary_game_agent": TaskType.EVOLVE_AGENT,
            "evolutionary_chatbot": TaskType.EVOLVE_AGENT,
            "self_modification": TaskType.OPTIMIZE_CODE,
        }

        task_type = task_type_map.get(analysis.suggested_approach, TaskType.LEARN_SKILL)

        # Create evolutionary parameters
        evolutionary_params = {
            "population_size": 10,
            "num_generations": 20,
            "mutation_rate": 0.3,
            "crossover_rate": 0.5,
            "elitism": 0.2,
            "domain": analysis.domain_name,
            "required_capabilities": analysis.required_capabilities
        }

        # Adjust parameters based on difficulty
        if analysis.estimated_difficulty > 0.7:
            evolutionary_params["population_size"] = 15
            evolutionary_params["num_generations"] = 30

        # Create meta-task
        meta_task = MetaTask(
            task_id=task_id,
            task_type=task_type,
            goal=user_goal,
            target_benchmark=analysis.relevant_benchmarks[0],
            target_fitness=target_fitness,
            evolutionary_parameters=evolutionary_params,
            time_budget=time_budget,
            created_timestamp=datetime.now().isoformat()
        )

        self.task_history.append(meta_task)

        self.logger.info(f"✓ Meta-task created: {task_id}")
        self.logger.info(f"  Task type: {task_type.value}")
        self.logger.info(f"  Target benchmark: {meta_task.target_benchmark}")
        self.logger.info(f"  Target fitness: {meta_task.target_fitness}")

        return meta_task

    def generate_smm_directive(self, meta_task: MetaTask) -> Dict[str, Any]:
        """
        Generate a directive for the SMM (EvolutionaryOrchestratorAgent)

        Args:
            meta_task: The meta-task to convert into SMM directive

        Returns:
            SMM directive dictionary
        """
        self.logger.info(f"🔧 Generating SMM directive for task: {meta_task.task_id}")

        if meta_task.task_type == TaskType.EVOLVE_AGENT:
            directive = {
                "directive_type": "evolve_domain_expert",
                "objective": meta_task.goal,
                "target_benchmark": meta_task.target_benchmark,
                "fitness_function": {
                    "type": "benchmark_fitness",
                    "benchmark_name": meta_task.target_benchmark,
                    "target_score": meta_task.target_fitness
                },
                "evolutionary_config": meta_task.evolutionary_parameters,
                "genome_template": "DomainExpertAgent",
                "termination_criteria": {
                    "max_generations": meta_task.evolutionary_parameters["num_generations"],
                    "target_fitness": meta_task.target_fitness,
                    "time_budget_seconds": meta_task.time_budget
                },
                "reporting": {
                    "report_frequency": 5,  # Report every 5 generations
                    "verbose": True
                }
            }

        elif meta_task.task_type == TaskType.OPTIMIZE_CODE:
            directive = {
                "directive_type": "self_optimize",
                "objective": meta_task.goal,
                "target_benchmark": meta_task.target_benchmark,
                "optimization_strategy": "iterative_improvement",
                "termination_criteria": {
                    "target_fitness": meta_task.target_fitness,
                    "time_budget_seconds": meta_task.time_budget
                }
            }

        else:
            # Generic directive
            directive = {
                "directive_type": "general_task",
                "objective": meta_task.goal,
                "target_benchmark": meta_task.target_benchmark,
                "target_fitness": meta_task.target_fitness
            }

        self.logger.info(f"✓ SMM directive generated")
        self.logger.info(f"  Directive type: {directive['directive_type']}")

        return directive

    def plan_capability_acquisition(self, user_goal: str) -> Tuple[MetaTask, Dict[str, Any]]:
        """
        Complete planning pipeline: from user goal to SMM directive

        Args:
            user_goal: High-level user goal

        Returns:
            Tuple of (MetaTask, SMM directive)
        """
        self.logger.info(f"🎯 Planning capability acquisition for: '{user_goal}'")

        # Step 1: Create meta-task
        meta_task = self.create_meta_task(user_goal)

        # Step 2: Generate SMM directive
        smm_directive = self.generate_smm_directive(meta_task)

        self.logger.info(f"✓ Planning complete for task: {meta_task.task_id}")

        return meta_task, smm_directive

    def update_task_progress(self, task_id: str, current_fitness: float, generation: int):
        """
        Update progress on a meta-task

        Args:
            task_id: Task identifier
            current_fitness: Current fitness achieved
            generation: Current generation number
        """
        for task in self.task_history:
            if task.task_id == task_id:
                progress = (current_fitness / task.target_fitness) * 100
                self.logger.info(f"📊 Task {task_id}: Generation {generation}, Fitness {current_fitness:.3f} ({progress:.1f}% of target)")
                break

    def evaluate_task_completion(self, task_id: str, final_fitness: float) -> bool:
        """
        Evaluate if a task has been completed successfully

        Args:
            task_id: Task identifier
            final_fitness: Final fitness achieved

        Returns:
            True if task completed successfully
        """
        for task in self.task_history:
            if task.task_id == task_id:
                success = final_fitness >= task.target_fitness
                status = "✓ SUCCESS" if success else "✗ INCOMPLETE"
                self.logger.info(f"{status} Task {task_id}: Final fitness {final_fitness:.3f} (target: {task.target_fitness})")
                return success

        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a task"""
        for task in self.task_history:
            if task.task_id == task_id:
                return {
                    "task_id": task.task_id,
                    "goal": task.goal,
                    "task_type": task.task_type.value,
                    "target_benchmark": task.target_benchmark,
                    "target_fitness": task.target_fitness,
                    "created": task.created_timestamp
                }
        return None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all meta-tasks in history"""
        return [asdict(task) for task in self.task_history]

    def suggest_next_goal(self, completed_goals: List[str]) -> str:
        """
        Suggest a next goal based on completed goals (curriculum learning)

        Args:
            completed_goals: List of successfully completed goals

        Returns:
            Suggested next goal
        """
        # Simple curriculum: progress from easier to harder domains
        curriculum = [
            "Learn to play Draughts",
            "Become a helpful chatbot",
            "Master Chess",
            "Optimize your own code"
        ]

        for goal in curriculum:
            if goal not in completed_goals:
                self.logger.info(f"💡 Suggested next goal: '{goal}'")
                return goal

        return "Continue self-improvement across all domains"