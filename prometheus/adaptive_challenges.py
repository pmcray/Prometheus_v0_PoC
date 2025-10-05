"""
Adaptive Challenge Creation System v0.1 (v0.60)
Dynamic curriculum generation and challenge adaptation

Implements intelligent challenge creation and adaptation:
- Adaptive difficulty based on agent capability
- Novel challenge generation from patterns
- Curriculum sequencing and progression
- Challenge diversity and novelty metrics
- Performance-based challenge customization
"""

import random
import statistics
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json
import ast

class ChallengeCategory(Enum):
    """Categories of programming challenges"""
    OPTIMIZATION = "optimization"
    ALGORITHMIC = "algorithmic"
    DATA_STRUCTURES = "data_structures"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    DESIGN_PATTERNS = "design_patterns"
    PERFORMANCE = "performance"
    SAFETY = "safety"

class DifficultyLevel(Enum):
    """Difficulty levels for challenges"""
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    MASTER = 5

@dataclass
class Challenge:
    """Represents a programming challenge"""
    challenge_id: str
    title: str
    description: str
    category: ChallengeCategory
    difficulty_level: DifficultyLevel
    initial_code: str
    target_output: Any
    success_criteria: Dict[str, Any]
    test_cases: List[Dict[str, Any]]
    hints: List[str]
    estimated_time_minutes: int
    prerequisite_skills: List[str]
    learning_objectives: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChallengeAttempt:
    """Records an attempt at solving a challenge"""
    attempt_id: str
    challenge_id: str
    agent_id: str
    submitted_code: str
    success: bool
    score: float
    execution_time_ms: float
    errors_encountered: List[str]
    feedback: str
    attempt_timestamp: str
    learning_progress: Dict[str, float]

@dataclass
class AgentProfile:
    """Profile tracking agent capabilities and progress"""
    agent_id: str
    skill_levels: Dict[str, float]  # Skill -> proficiency level (0.0 to 1.0)
    challenge_history: List[str]  # Challenge IDs attempted
    success_rates: Dict[ChallengeCategory, float]
    learning_preferences: Dict[str, Any]
    current_focus_areas: List[str]
    adaptive_parameters: Dict[str, float]
    last_updated: str

class ChallengeTemplate:
    """Templates for generating new challenges"""

    def __init__(self):
        self.optimization_templates = [
            {
                "pattern": "nested_loops",
                "description": "Optimize nested loop performance",
                "code_template": """
def optimize_nested_loops(data):
    result = []
    for i in range(len(data)):
        for j in range(len(data)):
            if data[i] {condition} data[j]:
                result.append({operation})
    return result
""",
                "variations": {
                    "condition": [">", "<", "==", "!="],
                    "operation": ["(i, j)", "data[i] + data[j]", "max(data[i], data[j])"]
                }
            },
            {
                "pattern": "string_processing",
                "description": "Optimize string manipulation",
                "code_template": """
def process_strings(strings):
    result = ""
    for s in strings:
        result += s.{method}() + " "
    return result.strip()
""",
                "variations": {
                    "method": ["upper", "lower", "title", "capitalize"]
                }
            }
        ]

        self.algorithmic_templates = [
            {
                "pattern": "sorting",
                "description": "Implement efficient sorting algorithm",
                "code_template": """
def sort_data(data):
    # Implement {algorithm} sort
    # TODO: Complete implementation
    return sorted(data)  # Replace with your implementation
""",
                "variations": {
                    "algorithm": ["bubble", "selection", "insertion", "merge", "quick"]
                }
            },
            {
                "pattern": "searching",
                "description": "Implement search algorithm",
                "code_template": """
def search_element(data, target):
    # Implement {algorithm} search
    # TODO: Complete implementation
    return target in data  # Replace with your implementation
""",
                "variations": {
                    "algorithm": ["linear", "binary", "exponential", "interpolation"]
                }
            }
        ]

        self.debugging_templates = [
            {
                "pattern": "logic_error",
                "description": "Fix logical error in implementation",
                "code_template": """
def calculate_average(numbers):
    total = 0
    count = 0
    for num in numbers:
        total += num
        count += 1
    return total / count  # Bug: Division by zero possible
""",
                "bug_types": ["division_by_zero", "off_by_one", "infinite_loop", "wrong_condition"]
            }
        ]

class AdaptiveChallengeGenerator:
    """Generates challenges adapted to agent capabilities"""

    def __init__(self):
        self.challenge_templates = ChallengeTemplate()
        self.generated_challenges: Dict[str, Challenge] = {}
        self.challenge_counter = 0

        # Skill progression mappings
        self.skill_dependencies = {
            "basic_syntax": [],
            "control_flow": ["basic_syntax"],
            "functions": ["basic_syntax", "control_flow"],
            "data_structures": ["basic_syntax", "functions"],
            "algorithms": ["functions", "data_structures", "control_flow"],
            "optimization": ["algorithms", "data_structures"],
            "design_patterns": ["functions", "data_structures"],
            "debugging": ["basic_syntax", "control_flow"],
            "refactoring": ["functions", "design_patterns"],
            "performance": ["algorithms", "optimization"]
        }

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def generate_challenge(self,
                         agent_profile: AgentProfile,
                         preferred_category: Optional[ChallengeCategory] = None,
                         target_difficulty: Optional[DifficultyLevel] = None) -> Challenge:
        """Generate a challenge adapted to the agent's current capabilities"""

        self.logger.info(f"🎯 Generating adaptive challenge for agent {agent_profile.agent_id}")

        # Determine optimal category and difficulty
        if not preferred_category:
            preferred_category = self._select_optimal_category(agent_profile)

        if not target_difficulty:
            target_difficulty = self._calculate_target_difficulty(agent_profile, preferred_category)

        # Select appropriate template
        template = self._select_template(preferred_category, target_difficulty)

        # Generate challenge from template
        challenge = self._instantiate_challenge(template, agent_profile, preferred_category, target_difficulty)

        # Store generated challenge
        self.generated_challenges[challenge.challenge_id] = challenge

        self.logger.info(f"✅ Generated {preferred_category.value} challenge: {challenge.title} "
                        f"(Difficulty: {target_difficulty.value})")

        return challenge

    def _select_optimal_category(self, agent_profile: AgentProfile) -> ChallengeCategory:
        """Select the best challenge category for skill development"""

        # Analyze agent's current strengths and weaknesses
        category_scores = {}

        for category in ChallengeCategory:
            success_rate = agent_profile.success_rates.get(category, 0.5)

            # Balance between challenge and achievability
            # Target categories where agent has moderate success (room for improvement)
            if 0.3 <= success_rate <= 0.7:
                category_scores[category] = 1.0  # Optimal challenge zone
            elif success_rate < 0.3:
                category_scores[category] = 0.7  # Too difficult, but still valuable
            else:
                category_scores[category] = 0.4  # Too easy, lower priority

        # Consider learning preferences
        for focus_area in agent_profile.current_focus_areas:
            for category in ChallengeCategory:
                if focus_area.lower() in category.value.lower():
                    category_scores[category] = category_scores.get(category, 0.5) * 1.3

        # Select category with highest score
        if category_scores:
            return max(category_scores.keys(), key=lambda k: category_scores[k])
        else:
            return random.choice(list(ChallengeCategory))

    def _calculate_target_difficulty(self, agent_profile: AgentProfile, category: ChallengeCategory) -> DifficultyLevel:
        """Calculate optimal difficulty level for the agent"""

        # Get agent's success rate in this category
        success_rate = agent_profile.success_rates.get(category, 0.5)

        # Map success rate to target difficulty
        if success_rate >= 0.9:
            return DifficultyLevel.EXPERT
        elif success_rate >= 0.75:
            return DifficultyLevel.ADVANCED
        elif success_rate >= 0.6:
            return DifficultyLevel.INTERMEDIATE
        elif success_rate >= 0.4:
            return DifficultyLevel.BEGINNER
        else:
            return DifficultyLevel.BEGINNER

    def _select_template(self, category: ChallengeCategory, difficulty: DifficultyLevel) -> Dict[str, Any]:
        """Select appropriate template based on category and difficulty"""

        if category == ChallengeCategory.OPTIMIZATION:
            return random.choice(self.challenge_templates.optimization_templates)
        elif category == ChallengeCategory.ALGORITHMIC:
            return random.choice(self.challenge_templates.algorithmic_templates)
        elif category == ChallengeCategory.DEBUGGING:
            return random.choice(self.challenge_templates.debugging_templates)
        else:
            # Generate generic template for other categories
            return self._create_generic_template(category, difficulty)

    def _create_generic_template(self, category: ChallengeCategory, difficulty: DifficultyLevel) -> Dict[str, Any]:
        """Create a generic template for categories without specific templates"""

        if category == ChallengeCategory.REFACTORING:
            return {
                "pattern": "refactoring",
                "description": "Refactor code for better maintainability",
                "code_template": """
def messy_function(data):
    # This function needs refactoring
    x = []
    for i in range(len(data)):
        if data[i] > 0:
            x.append(data[i] * 2)
    return x
""",
                "variations": {"task": ["extract methods", "improve naming", "reduce complexity"]}
            }

        elif category == ChallengeCategory.DESIGN_PATTERNS:
            return {
                "pattern": "design_pattern",
                "description": "Implement a design pattern",
                "code_template": """
# Implement the {pattern} pattern
class BaseClass:
    def method(self):
        pass

# TODO: Complete the pattern implementation
""",
                "variations": {"pattern": ["singleton", "observer", "factory", "strategy"]}
            }

        # Default template
        return {
            "pattern": "generic",
            "description": f"Solve a {category.value} problem",
            "code_template": """
def solve_problem(input_data):
    # TODO: Implement solution
    return None
""",
            "variations": {}
        }

    def _instantiate_challenge(self,
                             template: Dict[str, Any],
                             agent_profile: AgentProfile,
                             category: ChallengeCategory,
                             difficulty: DifficultyLevel) -> Challenge:
        """Instantiate a concrete challenge from a template"""

        self.challenge_counter += 1
        challenge_id = f"adaptive_{self.challenge_counter}_{category.value}_{difficulty.value}"

        # Apply template variations
        code_template = template["code_template"]
        variations = template.get("variations", {})

        for placeholder, options in variations.items():
            selected_option = random.choice(options)
            code_template = code_template.replace(f"{{{placeholder}}}", str(selected_option))

        # Generate test cases based on difficulty
        test_cases = self._generate_test_cases(category, difficulty, code_template)

        # Create learning objectives
        learning_objectives = self._generate_learning_objectives(category, difficulty)

        # Estimate time based on difficulty and agent profile
        estimated_time = self._estimate_completion_time(agent_profile, category, difficulty)

        challenge = Challenge(
            challenge_id=challenge_id,
            title=f"{category.value.title()} Challenge #{self.challenge_counter}",
            description=template["description"],
            category=category,
            difficulty_level=difficulty,
            initial_code=code_template,
            target_output=None,  # To be determined by test cases
            success_criteria={
                "min_test_cases_passed": max(1, len(test_cases) // 2),
                "execution_time_limit_ms": 1000 * (difficulty.value + 1),
                "code_quality_threshold": 0.6
            },
            test_cases=test_cases,
            hints=self._generate_hints(category, difficulty, template),
            estimated_time_minutes=estimated_time,
            prerequisite_skills=self._get_prerequisite_skills(category),
            learning_objectives=learning_objectives,
            metadata={
                "template_pattern": template["pattern"],
                "generated_for_agent": agent_profile.agent_id,
                "generation_timestamp": datetime.now().isoformat(),
                "adaptations_applied": self._get_applied_adaptations(agent_profile, category)
            }
        )

        return challenge

    def _generate_test_cases(self, category: ChallengeCategory, difficulty: DifficultyLevel, code: str) -> List[Dict[str, Any]]:
        """Generate test cases for the challenge"""

        test_cases = []
        num_cases = min(2 + difficulty.value, 8)  # 3-8 test cases based on difficulty

        if category == ChallengeCategory.OPTIMIZATION:
            # Generate test cases for optimization challenges
            for i in range(num_cases):
                size = 5 + i * (5 + difficulty.value)
                input_data = list(range(size))
                random.shuffle(input_data)

                test_cases.append({
                    "input": {"data": input_data},
                    "expected_output": sorted(input_data),  # Simplified expectation
                    "description": f"Test case {i+1}: data size {size}",
                    "performance_threshold_ms": 100 * (difficulty.value + 1)
                })

        elif category == ChallengeCategory.ALGORITHMIC:
            # Generate algorithmic test cases
            for i in range(num_cases):
                size = 3 + i * 2
                input_data = [random.randint(1, 100) for _ in range(size)]

                test_cases.append({
                    "input": {"data": input_data},
                    "expected_behavior": "correct_algorithm_implementation",
                    "description": f"Algorithm test {i+1}",
                    "correctness_required": True
                })

        else:
            # Generic test cases
            for i in range(num_cases):
                test_cases.append({
                    "input": {"test_data": f"test_{i}"},
                    "expected_output": f"expected_{i}",
                    "description": f"Generic test case {i+1}"
                })

        return test_cases

    def _generate_learning_objectives(self, category: ChallengeCategory, difficulty: DifficultyLevel) -> List[str]:
        """Generate learning objectives for the challenge"""

        base_objectives = {
            ChallengeCategory.OPTIMIZATION: [
                "Understand algorithm time complexity",
                "Learn optimization techniques",
                "Practice performance analysis"
            ],
            ChallengeCategory.ALGORITHMIC: [
                "Master fundamental algorithms",
                "Develop problem-solving skills",
                "Learn algorithm design patterns"
            ],
            ChallengeCategory.DEBUGGING: [
                "Develop debugging skills",
                "Learn error identification",
                "Practice systematic problem solving"
            ],
            ChallengeCategory.REFACTORING: [
                "Understand code quality principles",
                "Learn refactoring techniques",
                "Practice clean code writing"
            ]
        }

        objectives = base_objectives.get(category, ["Learn programming concepts"])

        # Add difficulty-specific objectives
        if difficulty.value >= 3:
            objectives.append("Apply advanced techniques")
        if difficulty.value >= 4:
            objectives.append("Optimize for edge cases")

        return objectives

    def _estimate_completion_time(self, agent_profile: AgentProfile, category: ChallengeCategory, difficulty: DifficultyLevel) -> int:
        """Estimate completion time based on agent profile and challenge parameters"""

        # Base time by difficulty
        base_time = {
            DifficultyLevel.BEGINNER: 15,
            DifficultyLevel.INTERMEDIATE: 30,
            DifficultyLevel.ADVANCED: 45,
            DifficultyLevel.EXPERT: 60,
            DifficultyLevel.MASTER: 90
        }

        estimated = base_time[difficulty]

        # Adjust based on agent's success rate in this category
        success_rate = agent_profile.success_rates.get(category, 0.5)
        if success_rate > 0.8:
            estimated = int(estimated * 0.7)  # Faster for experienced agent
        elif success_rate < 0.3:
            estimated = int(estimated * 1.5)  # Slower for struggling agent

        return estimated

    def _generate_hints(self, category: ChallengeCategory, difficulty: DifficultyLevel, template: Dict[str, Any]) -> List[str]:
        """Generate hints for the challenge"""

        hints = []

        if difficulty.value <= 2:  # Beginner/Intermediate
            hints.extend([
                "Start by understanding the problem requirements",
                "Break down the problem into smaller steps",
                "Test your solution with simple inputs first"
            ])

        if category == ChallengeCategory.OPTIMIZATION:
            hints.extend([
                "Consider the time complexity of your current approach",
                "Look for redundant operations that can be eliminated",
                "Think about more efficient data structures"
            ])

        elif category == ChallengeCategory.DEBUGGING:
            hints.extend([
                "Read error messages carefully",
                "Use print statements to trace execution",
                "Check boundary conditions and edge cases"
            ])

        # Limit hints based on difficulty (fewer hints for harder challenges)
        max_hints = max(1, 5 - difficulty.value)
        return hints[:max_hints]

    def _get_prerequisite_skills(self, category: ChallengeCategory) -> List[str]:
        """Get prerequisite skills for a challenge category"""

        skill_map = {
            ChallengeCategory.OPTIMIZATION: ["algorithms", "data_structures", "performance"],
            ChallengeCategory.ALGORITHMIC: ["basic_syntax", "control_flow", "functions"],
            ChallengeCategory.DEBUGGING: ["basic_syntax", "control_flow"],
            ChallengeCategory.REFACTORING: ["functions", "design_patterns"],
            ChallengeCategory.DESIGN_PATTERNS: ["functions", "data_structures"]
        }

        return skill_map.get(category, ["basic_syntax"])

    def _get_applied_adaptations(self, agent_profile: AgentProfile, category: ChallengeCategory) -> List[str]:
        """Record what adaptations were applied for this agent"""

        adaptations = []

        # Check success rate adaptation
        success_rate = agent_profile.success_rates.get(category, 0.5)
        if success_rate < 0.3:
            adaptations.append("reduced_difficulty_for_struggling_agent")
        elif success_rate > 0.8:
            adaptations.append("increased_difficulty_for_advanced_agent")

        # Check focus area adaptation
        if any(focus in category.value for focus in agent_profile.current_focus_areas):
            adaptations.append("aligned_with_focus_areas")

        return adaptations

    def adapt_existing_challenge(self, challenge: Challenge, agent_performance: ChallengeAttempt) -> Challenge:
        """Adapt an existing challenge based on agent performance"""

        self.logger.info(f"🔄 Adapting challenge {challenge.challenge_id} based on performance")

        adapted_challenge = Challenge(
            challenge_id=f"{challenge.challenge_id}_adapted_{len(agent_performance.errors_encountered)}",
            title=f"{challenge.title} (Adapted)",
            description=challenge.description,
            category=challenge.category,
            difficulty_level=challenge.difficulty_level,
            initial_code=challenge.initial_code,
            target_output=challenge.target_output,
            success_criteria=challenge.success_criteria.copy(),
            test_cases=challenge.test_cases.copy(),
            hints=challenge.hints.copy(),
            estimated_time_minutes=challenge.estimated_time_minutes,
            prerequisite_skills=challenge.prerequisite_skills,
            learning_objectives=challenge.learning_objectives,
            metadata=challenge.metadata.copy()
        )

        # Adapt based on performance
        if not agent_performance.success:
            if agent_performance.score < 0.3:
                # Major adaptation needed
                adapted_challenge.hints.extend([
                    "Consider this specific approach for your solution",
                    "Focus on getting a basic working solution first"
                ])
                adapted_challenge.estimated_time_minutes = int(adapted_challenge.estimated_time_minutes * 1.5)

                # Add easier test cases
                simple_test = {
                    "input": {"data": [1, 2, 3]},
                    "expected_output": [1, 2, 3],
                    "description": "Simple test case",
                    "is_tutorial": True
                }
                adapted_challenge.test_cases.insert(0, simple_test)

            elif len(agent_performance.errors_encountered) > 0:
                # Specific error-based hints
                for error in agent_performance.errors_encountered:
                    if "syntax" in error.lower():
                        adapted_challenge.hints.append("Check your syntax carefully, especially brackets and colons")
                    elif "indentation" in error.lower():
                        adapted_challenge.hints.append("Python requires consistent indentation")
                    elif "name" in error.lower():
                        adapted_challenge.hints.append("Make sure all variable names are defined before use")

        adapted_challenge.metadata["adaptation_reason"] = "performance_based"
        adapted_challenge.metadata["original_challenge_id"] = challenge.challenge_id
        adapted_challenge.metadata["adaptation_timestamp"] = datetime.now().isoformat()

        return adapted_challenge

    def get_generation_statistics(self) -> Dict[str, Any]:
        """Get statistics about challenge generation"""

        if not self.generated_challenges:
            return {"total_challenges": 0}

        challenges = list(self.generated_challenges.values())

        category_counts = {}
        difficulty_counts = {}

        for challenge in challenges:
            category_counts[challenge.category.value] = category_counts.get(challenge.category.value, 0) + 1
            difficulty_counts[challenge.difficulty_level.value] = difficulty_counts.get(challenge.difficulty_level.value, 0) + 1

        return {
            "total_challenges": len(challenges),
            "category_distribution": category_counts,
            "difficulty_distribution": difficulty_counts,
            "average_estimated_time": statistics.mean([c.estimated_time_minutes for c in challenges]),
            "unique_templates_used": len(set(c.metadata.get("template_pattern", "unknown") for c in challenges))
        }