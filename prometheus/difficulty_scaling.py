"""
Difficulty Scaling System v0.1 (v0.61)
Intelligent difficulty adjustment and progression tracking

Implements sophisticated difficulty scaling mechanisms:
- Dynamic difficulty adjustment based on performance
- Skill-based progression tracking
- Adaptive challenge complexity
- Zone of proximal development optimization
- Multi-dimensional difficulty modeling
"""

import random
import statistics
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json

from .adaptive_challenges import Challenge, ChallengeAttempt, AgentProfile, DifficultyLevel, ChallengeCategory

class ProgressionState(Enum):
    """States of learning progression"""
    STRUGGLING = "struggling"          # Below comfort zone
    LEARNING = "learning"              # In zone of proximal development
    MASTERING = "mastering"            # Approaching mastery
    MASTERED = "mastered"              # Skill mastered
    PLATEAU = "plateau"                # Progress stalled

@dataclass
class SkillMetrics:
    """Comprehensive skill assessment metrics"""
    current_level: float                # 0.0 to 1.0
    confidence_interval: Tuple[float, float]
    learning_velocity: float           # Rate of improvement
    consistency_score: float           # How consistent performance is
    retention_rate: float              # How well skills are retained
    transfer_ability: float            # How well skills transfer to new contexts
    last_assessment: str
    assessment_history: List[Tuple[str, float]] = field(default_factory=list)

@dataclass
class DifficultyDimension:
    """Represents one dimension of difficulty"""
    dimension_name: str
    current_value: float               # 0.0 to 1.0
    min_value: float = 0.0
    max_value: float = 1.0
    step_size: float = 0.1
    description: str = ""

@dataclass
class DifficultyProfile:
    """Multi-dimensional difficulty profile"""
    profile_id: str
    dimensions: Dict[str, DifficultyDimension]
    overall_difficulty: float
    complexity_factors: Dict[str, float]
    agent_suitability: float           # How suitable for specific agent
    generation_params: Dict[str, Any]

@dataclass
class ProgressionPlan:
    """Personalized progression plan for an agent"""
    agent_id: str
    current_stage: str
    target_skills: List[str]
    progression_path: List[Dict[str, Any]]
    estimated_timeline: Dict[str, int]  # Skill -> estimated days to proficiency
    next_milestones: List[str]
    adaptive_parameters: Dict[str, float]

class MultiDimensionalDifficulty:
    """Models difficulty across multiple dimensions"""

    def __init__(self):
        # Define difficulty dimensions
        self.dimension_definitions = {
            "cognitive_load": {
                "description": "Mental effort required",
                "factors": ["problem_complexity", "abstraction_level", "working_memory_demand"]
            },
            "technical_complexity": {
                "description": "Technical skill requirements",
                "factors": ["syntax_complexity", "algorithm_difficulty", "data_structure_complexity"]
            },
            "problem_size": {
                "description": "Scale and scope of the problem",
                "factors": ["input_size", "output_complexity", "edge_cases"]
            },
            "time_pressure": {
                "description": "Time constraints and efficiency requirements",
                "factors": ["execution_time_limits", "development_time_pressure"]
            },
            "creativity_required": {
                "description": "Level of creative thinking needed",
                "factors": ["novel_approaches", "multiple_solutions", "design_freedom"]
            },
            "domain_knowledge": {
                "description": "Specialized knowledge requirements",
                "factors": ["domain_concepts", "specialized_libraries", "industry_context"]
            }
        }

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def create_difficulty_profile(self,
                                challenge: Challenge,
                                target_agent: AgentProfile) -> DifficultyProfile:
        """Create a comprehensive difficulty profile for a challenge"""

        dimensions = {}

        # Analyze cognitive load
        dimensions["cognitive_load"] = self._assess_cognitive_load(challenge)

        # Analyze technical complexity
        dimensions["technical_complexity"] = self._assess_technical_complexity(challenge)

        # Analyze problem size
        dimensions["problem_size"] = self._assess_problem_size(challenge)

        # Analyze time pressure
        dimensions["time_pressure"] = self._assess_time_pressure(challenge)

        # Analyze creativity requirements
        dimensions["creativity_required"] = self._assess_creativity_requirements(challenge)

        # Analyze domain knowledge requirements
        dimensions["domain_knowledge"] = self._assess_domain_knowledge(challenge)

        # Calculate overall difficulty
        overall_difficulty = self._calculate_overall_difficulty(dimensions)

        # Calculate agent suitability
        agent_suitability = self._calculate_agent_suitability(dimensions, target_agent)

        profile = DifficultyProfile(
            profile_id=f"diff_profile_{challenge.challenge_id}",
            dimensions=dimensions,
            overall_difficulty=overall_difficulty,
            complexity_factors=self._extract_complexity_factors(challenge),
            agent_suitability=agent_suitability,
            generation_params=self._generate_difficulty_params(dimensions)
        )

        return profile

    def _assess_cognitive_load(self, challenge: Challenge) -> DifficultyDimension:
        """Assess cognitive load dimension"""
        code_complexity = len(challenge.initial_code.split('\n'))
        abstraction_level = challenge.initial_code.count('class') * 0.3 + challenge.initial_code.count('def') * 0.2

        # Normalize to 0-1 range
        complexity_score = min(1.0, code_complexity / 50.0)
        abstraction_score = min(1.0, abstraction_level / 10.0)

        cognitive_load = (complexity_score + abstraction_score) / 2.0

        return DifficultyDimension(
            dimension_name="cognitive_load",
            current_value=cognitive_load,
            description="Mental effort and working memory demands"
        )

    def _assess_technical_complexity(self, challenge: Challenge) -> DifficultyDimension:
        """Assess technical complexity dimension"""
        # Analyze code patterns and constructs
        advanced_patterns = [
            'lambda', 'comprehension', 'decorator', 'generator', 'async', 'yield',
            'metaclass', 'property', '__getattr__', 'isinstance'
        ]

        pattern_count = sum(1 for pattern in advanced_patterns if pattern in challenge.initial_code.lower())
        syntax_complexity = min(1.0, pattern_count / len(advanced_patterns))

        # Factor in challenge category
        category_complexity = {
            ChallengeCategory.OPTIMIZATION: 0.8,
            ChallengeCategory.ALGORITHMIC: 0.7,
            ChallengeCategory.DESIGN_PATTERNS: 0.9,
            ChallengeCategory.DEBUGGING: 0.6,
            ChallengeCategory.REFACTORING: 0.5,
            ChallengeCategory.DATA_STRUCTURES: 0.8,
            ChallengeCategory.PERFORMANCE: 0.9,
            ChallengeCategory.SAFETY: 0.7
        }.get(challenge.category, 0.5)

        technical_complexity = (syntax_complexity + category_complexity) / 2.0

        return DifficultyDimension(
            dimension_name="technical_complexity",
            current_value=technical_complexity,
            description="Technical skill and syntax requirements"
        )

    def _assess_problem_size(self, challenge: Challenge) -> DifficultyDimension:
        """Assess problem size and scope"""
        # Consider test cases, code length, and expected complexity
        num_test_cases = len(challenge.test_cases)
        code_length = len(challenge.initial_code)

        size_score = min(1.0, (num_test_cases / 10.0 + code_length / 500.0) / 2.0)

        return DifficultyDimension(
            dimension_name="problem_size",
            current_value=size_score,
            description="Scale and scope of the problem"
        )

    def _assess_time_pressure(self, challenge: Challenge) -> DifficultyDimension:
        """Assess time pressure dimension"""
        estimated_time = challenge.estimated_time_minutes
        time_limits = challenge.success_criteria.get("execution_time_limit_ms", 5000)

        # Shorter estimated time and stricter limits = higher time pressure
        time_pressure_score = min(1.0, (60 - estimated_time) / 60.0 + (5000 - time_limits) / 5000.0) / 2.0
        time_pressure_score = max(0.0, time_pressure_score)

        return DifficultyDimension(
            dimension_name="time_pressure",
            current_value=time_pressure_score,
            description="Time constraints and efficiency requirements"
        )

    def _assess_creativity_requirements(self, challenge: Challenge) -> DifficultyDimension:
        """Assess creativity requirements"""
        # Look for open-ended aspects
        open_ended_keywords = ['design', 'implement', 'create', 'optimize', 'improve', 'refactor']
        creativity_indicators = sum(1 for keyword in open_ended_keywords
                                  if keyword in challenge.description.lower())

        creativity_score = min(1.0, creativity_indicators / len(open_ended_keywords))

        # Design patterns and refactoring typically require more creativity
        if challenge.category in [ChallengeCategory.DESIGN_PATTERNS, ChallengeCategory.REFACTORING]:
            creativity_score = max(creativity_score, 0.7)

        return DifficultyDimension(
            dimension_name="creativity_required",
            current_value=creativity_score,
            description="Level of creative and innovative thinking required"
        )

    def _assess_domain_knowledge(self, challenge: Challenge) -> DifficultyDimension:
        """Assess domain-specific knowledge requirements"""
        # Check for specialized concepts
        domain_keywords = {
            'algorithms': ['sort', 'search', 'tree', 'graph', 'hash'],
            'data_science': ['data', 'analysis', 'statistics', 'model'],
            'web': ['http', 'api', 'request', 'response', 'json'],
            'systems': ['performance', 'memory', 'cpu', 'optimization'],
            'security': ['encrypt', 'decrypt', 'hash', 'secure', 'auth']
        }

        domain_score = 0.0
        for domain, keywords in domain_keywords.items():
            matches = sum(1 for keyword in keywords
                         if keyword in challenge.description.lower() or keyword in challenge.initial_code.lower())
            if matches > 0:
                domain_score = max(domain_score, matches / len(keywords))

        return DifficultyDimension(
            dimension_name="domain_knowledge",
            current_value=domain_score,
            description="Specialized domain knowledge requirements"
        )

    def _calculate_overall_difficulty(self, dimensions: Dict[str, DifficultyDimension]) -> float:
        """Calculate overall difficulty from dimensions"""
        # Weighted average of dimensions
        weights = {
            "cognitive_load": 0.25,
            "technical_complexity": 0.25,
            "problem_size": 0.15,
            "time_pressure": 0.10,
            "creativity_required": 0.15,
            "domain_knowledge": 0.10
        }

        weighted_sum = sum(dimensions[dim].current_value * weights.get(dim, 0.1)
                          for dim in dimensions)

        return min(1.0, weighted_sum)

    def _calculate_agent_suitability(self, dimensions: Dict[str, DifficultyDimension],
                                   agent: AgentProfile) -> float:
        """Calculate how suitable this difficulty profile is for the agent"""
        suitability_scores = []

        # Check alignment with agent's skill levels
        for dim_name, dimension in dimensions.items():
            # Map dimension to relevant skills
            relevant_skills = self._map_dimension_to_skills(dim_name)

            if relevant_skills:
                agent_skill_level = np.mean([agent.skill_levels.get(skill, 0.5)
                                           for skill in relevant_skills])

                # Optimal difficulty is slightly above current skill level
                optimal_challenge_level = min(1.0, agent_skill_level + 0.2)

                # Calculate how close the dimension is to optimal
                distance = abs(dimension.current_value - optimal_challenge_level)
                suitability = max(0.0, 1.0 - distance * 2.0)  # Penalize large distances
                suitability_scores.append(suitability)

        return np.mean(suitability_scores) if suitability_scores else 0.5

    def _map_dimension_to_skills(self, dimension_name: str) -> List[str]:
        """Map difficulty dimension to relevant skills"""
        mapping = {
            "cognitive_load": ["problem_solving", "abstraction", "working_memory"],
            "technical_complexity": ["syntax", "algorithms", "data_structures"],
            "problem_size": ["decomposition", "modularization", "testing"],
            "time_pressure": ["efficiency", "optimization", "prioritization"],
            "creativity_required": ["design", "innovation", "flexibility"],
            "domain_knowledge": ["domain_expertise", "specialized_knowledge"]
        }
        return mapping.get(dimension_name, [])

    def _extract_complexity_factors(self, challenge: Challenge) -> Dict[str, float]:
        """Extract specific complexity factors"""
        factors = {}

        # Code analysis
        code = challenge.initial_code
        factors["lines_of_code"] = len(code.split('\n'))
        factors["cyclomatic_complexity"] = code.count('if') + code.count('for') + code.count('while')
        factors["function_count"] = code.count('def')
        factors["class_count"] = code.count('class')

        # Challenge analysis
        factors["test_case_count"] = len(challenge.test_cases)
        factors["hint_count"] = len(challenge.hints)
        factors["prerequisite_count"] = len(challenge.prerequisite_skills)

        # Normalize factors
        max_values = {
            "lines_of_code": 100,
            "cyclomatic_complexity": 20,
            "function_count": 10,
            "class_count": 5,
            "test_case_count": 10,
            "hint_count": 10,
            "prerequisite_count": 5
        }

        normalized_factors = {}
        for factor, value in factors.items():
            max_val = max_values.get(factor, 10)
            normalized_factors[factor] = min(1.0, value / max_val)

        return normalized_factors

    def _generate_difficulty_params(self, dimensions: Dict[str, DifficultyDimension]) -> Dict[str, Any]:
        """Generate parameters for difficulty-based challenge generation"""
        params = {}

        for dim_name, dimension in dimensions.items():
            params[f"{dim_name}_level"] = dimension.current_value
            params[f"{dim_name}_adjustment"] = dimension.step_size

        params["overall_difficulty"] = self._calculate_overall_difficulty(dimensions)
        return params

class ProgressionTracker:
    """Tracks learning progression and skill development"""

    def __init__(self):
        self.skill_assessments: Dict[str, Dict[str, SkillMetrics]] = {}  # agent_id -> skill -> metrics
        self.progression_history: Dict[str, List[Dict[str, Any]]] = {}   # agent_id -> history

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def assess_skill_level(self, agent_id: str, skill_name: str,
                          recent_attempts: List[ChallengeAttempt]) -> SkillMetrics:
        """Assess current skill level based on recent performance"""

        if not recent_attempts:
            return SkillMetrics(
                current_level=0.5,
                confidence_interval=(0.3, 0.7),
                learning_velocity=0.0,
                consistency_score=0.5,
                retention_rate=0.5,
                transfer_ability=0.5,
                last_assessment=datetime.now().isoformat(),
                assessment_history=[]
            )

        # Calculate performance metrics
        scores = [attempt.score for attempt in recent_attempts if attempt.score is not None]
        success_rates = [1.0 if attempt.success else 0.0 for attempt in recent_attempts]

        if not scores:
            current_level = 0.5
        else:
            current_level = np.mean(scores)

        # Calculate confidence interval
        if len(scores) > 1:
            std_dev = np.std(scores)
            ci_lower = max(0.0, current_level - 1.96 * std_dev / np.sqrt(len(scores)))
            ci_upper = min(1.0, current_level + 1.96 * std_dev / np.sqrt(len(scores)))
        else:
            ci_lower, ci_upper = current_level - 0.2, current_level + 0.2

        # Calculate learning velocity (improvement over time)
        learning_velocity = 0.0
        if len(scores) >= 3:
            # Linear regression to estimate improvement trend
            x = np.arange(len(scores))
            slope = np.polyfit(x, scores, 1)[0]
            learning_velocity = max(-1.0, min(1.0, slope * len(scores)))  # Normalize

        # Calculate consistency score
        consistency_score = 1.0 - (np.std(scores) if len(scores) > 1 else 0.5)

        # Calculate retention rate (performance doesn't degrade over gaps)
        retention_rate = self._calculate_retention_rate(recent_attempts)

        # Calculate transfer ability (performance on related challenges)
        transfer_ability = self._calculate_transfer_ability(agent_id, skill_name, recent_attempts)

        metrics = SkillMetrics(
            current_level=current_level,
            confidence_interval=(ci_lower, ci_upper),
            learning_velocity=learning_velocity,
            consistency_score=consistency_score,
            retention_rate=retention_rate,
            transfer_ability=transfer_ability,
            last_assessment=datetime.now().isoformat()
        )

        # Store assessment
        if agent_id not in self.skill_assessments:
            self.skill_assessments[agent_id] = {}

        if skill_name not in self.skill_assessments[agent_id]:
            self.skill_assessments[agent_id][skill_name] = metrics
        else:
            # Update history
            old_metrics = self.skill_assessments[agent_id][skill_name]
            metrics.assessment_history = old_metrics.assessment_history + [
                (old_metrics.last_assessment, old_metrics.current_level)
            ]
            self.skill_assessments[agent_id][skill_name] = metrics

        return metrics

    def determine_progression_state(self, agent_id: str, skill_name: str) -> ProgressionState:
        """Determine the current progression state for a skill"""

        if agent_id not in self.skill_assessments or skill_name not in self.skill_assessments[agent_id]:
            return ProgressionState.LEARNING

        metrics = self.skill_assessments[agent_id][skill_name]

        # Analyze progression state
        if metrics.current_level < 0.3:
            return ProgressionState.STRUGGLING
        elif metrics.current_level >= 0.9 and metrics.consistency_score > 0.8:
            return ProgressionState.MASTERED
        elif metrics.current_level >= 0.7 and metrics.learning_velocity < 0.1:
            if metrics.consistency_score > 0.7:
                return ProgressionState.MASTERING
            else:
                return ProgressionState.PLATEAU
        elif metrics.learning_velocity > 0.1:
            return ProgressionState.LEARNING
        else:
            return ProgressionState.PLATEAU

    def _calculate_retention_rate(self, recent_attempts: List[ChallengeAttempt]) -> float:
        """Calculate how well skills are retained over time gaps"""
        if len(recent_attempts) < 3:
            return 0.5

        # Sort by timestamp
        sorted_attempts = sorted(recent_attempts, key=lambda x: x.attempt_timestamp)

        retention_scores = []
        for i in range(1, len(sorted_attempts)):
            prev_attempt = sorted_attempts[i-1]
            curr_attempt = sorted_attempts[i]

            # Calculate time gap
            prev_time = datetime.fromisoformat(prev_attempt.attempt_timestamp)
            curr_time = datetime.fromisoformat(curr_attempt.attempt_timestamp)
            time_gap = (curr_time - prev_time).days

            # Compare performance accounting for time gap
            if time_gap > 0:
                expected_decay = min(0.5, time_gap * 0.01)  # Assume 1% decay per day
                expected_score = max(0.0, prev_attempt.score - expected_decay)

                if curr_attempt.score >= expected_score:
                    retention_scores.append(1.0)
                else:
                    retention_scores.append(curr_attempt.score / expected_score)

        return np.mean(retention_scores) if retention_scores else 0.5

    def _calculate_transfer_ability(self, agent_id: str, skill_name: str,
                                  recent_attempts: List[ChallengeAttempt]) -> float:
        """Calculate how well skills transfer to new contexts"""
        # This is a simplified calculation
        # In practice, would analyze performance on challenges requiring similar skills

        if len(recent_attempts) < 2:
            return 0.5

        # Look for performance consistency across different challenge types
        category_performance = {}
        for attempt in recent_attempts:
            # Would need to lookup challenge category from attempt
            # For now, use simplified approach
            category = "general"  # Placeholder
            if category not in category_performance:
                category_performance[category] = []
            category_performance[category].append(attempt.score)

        if len(category_performance) > 1:
            # Calculate variance across categories
            category_means = [np.mean(scores) for scores in category_performance.values()]
            transfer_ability = 1.0 - np.std(category_means)
        else:
            # Not enough category diversity
            transfer_ability = 0.5

        return max(0.0, min(1.0, transfer_ability))

class AdaptiveDifficultyScaler:
    """Main system for adaptive difficulty scaling"""

    def __init__(self):
        self.multi_dimensional_difficulty = MultiDimensionalDifficulty()
        self.progression_tracker = ProgressionTracker()

        # Zone of proximal development parameters
        self.zpd_lower_bound = 0.1  # Below current skill level
        self.zpd_upper_bound = 0.3  # Above current skill level

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def scale_challenge_difficulty(self, challenge: Challenge, agent_profile: AgentProfile,
                                 recent_attempts: List[ChallengeAttempt]) -> Challenge:
        """Scale challenge difficulty to optimal level for agent"""

        self.logger.info(f"🎚️ Scaling difficulty for challenge {challenge.challenge_id}")

        # Create difficulty profile
        difficulty_profile = self.multi_dimensional_difficulty.create_difficulty_profile(
            challenge, agent_profile
        )

        # Assess relevant skills
        relevant_skills = challenge.prerequisite_skills
        skill_assessments = {}

        for skill in relevant_skills:
            skill_attempts = [attempt for attempt in recent_attempts
                            if skill in self._get_attempt_skills(attempt)]
            skill_assessments[skill] = self.progression_tracker.assess_skill_level(
                agent_profile.agent_id, skill, skill_attempts
            )

        # Determine optimal difficulty adjustment
        adjustment_factor = self._calculate_difficulty_adjustment(
            difficulty_profile, skill_assessments, agent_profile
        )

        # Apply difficulty scaling
        scaled_challenge = self._apply_difficulty_scaling(
            challenge, adjustment_factor, difficulty_profile
        )

        self.logger.info(f"✅ Scaled difficulty by factor {adjustment_factor:.2f}")

        return scaled_challenge

    def _get_attempt_skills(self, attempt: ChallengeAttempt) -> List[str]:
        """Extract skills from challenge attempt (placeholder)"""
        # In practice, would analyze the challenge and code to determine skills used
        return ["basic_syntax", "problem_solving"]

    def _calculate_difficulty_adjustment(self, difficulty_profile: DifficultyProfile,
                                       skill_assessments: Dict[str, SkillMetrics],
                                       agent_profile: AgentProfile) -> float:
        """Calculate how much to adjust difficulty"""

        if not skill_assessments:
            return 1.0  # No adjustment if no skill data

        # Calculate average skill level
        avg_skill_level = np.mean([metrics.current_level for metrics in skill_assessments.values()])

        # Calculate optimal challenge level (within zone of proximal development)
        optimal_level = avg_skill_level + (self.zpd_lower_bound + self.zpd_upper_bound) / 2

        # Compare with current difficulty
        current_difficulty = difficulty_profile.overall_difficulty

        # Calculate adjustment factor
        if current_difficulty == 0:
            adjustment_factor = 1.0
        else:
            adjustment_factor = optimal_level / current_difficulty

        # Constrain adjustment to reasonable bounds
        adjustment_factor = max(0.5, min(2.0, adjustment_factor))

        # Consider agent's learning velocity
        avg_learning_velocity = np.mean([metrics.learning_velocity for metrics in skill_assessments.values()])

        if avg_learning_velocity > 0.2:  # Fast learner
            adjustment_factor = min(2.0, adjustment_factor * 1.2)
        elif avg_learning_velocity < -0.1:  # Struggling learner
            adjustment_factor = max(0.5, adjustment_factor * 0.8)

        return adjustment_factor

    def _apply_difficulty_scaling(self, challenge: Challenge, adjustment_factor: float,
                                difficulty_profile: DifficultyProfile) -> Challenge:
        """Apply difficulty scaling to create modified challenge"""

        scaled_challenge = Challenge(
            challenge_id=f"{challenge.challenge_id}_scaled_{adjustment_factor:.2f}",
            title=challenge.title + f" (Scaled: {adjustment_factor:.2f}x)",
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

        # Apply scaling to different aspects
        if adjustment_factor < 1.0:  # Make easier
            # Add more hints
            if len(scaled_challenge.hints) < 5:
                scaled_challenge.hints.extend([
                    "Consider breaking this problem into smaller parts",
                    "Start with a simple approach, then optimize if needed"
                ])

            # Extend time limit
            scaled_challenge.estimated_time_minutes = int(challenge.estimated_time_minutes * 1.5)

            # Relax performance criteria
            if "execution_time_limit_ms" in scaled_challenge.success_criteria:
                scaled_challenge.success_criteria["execution_time_limit_ms"] *= 2

            # Simplify test cases
            if len(scaled_challenge.test_cases) > 3:
                # Keep only the simpler test cases
                scaled_challenge.test_cases = scaled_challenge.test_cases[:3]

        elif adjustment_factor > 1.0:  # Make harder
            # Remove some hints
            if len(scaled_challenge.hints) > 1:
                scaled_challenge.hints = scaled_challenge.hints[:max(1, len(scaled_challenge.hints) // 2)]

            # Reduce time limit
            scaled_challenge.estimated_time_minutes = max(10, int(challenge.estimated_time_minutes * 0.8))

            # Tighten performance criteria
            if "execution_time_limit_ms" in scaled_challenge.success_criteria:
                scaled_challenge.success_criteria["execution_time_limit_ms"] = int(
                    scaled_challenge.success_criteria["execution_time_limit_ms"] * 0.7
                )

            # Add more challenging test cases
            additional_test = {
                "input": {"data": list(range(100, 0, -1))},  # Large reverse-sorted data
                "expected_output": list(range(1, 101)),
                "description": "Large dataset test case",
                "performance_critical": True
            }
            scaled_challenge.test_cases.append(additional_test)

        # Update metadata
        scaled_challenge.metadata.update({
            "difficulty_scaling_applied": adjustment_factor,
            "original_challenge_id": challenge.challenge_id,
            "scaling_timestamp": datetime.now().isoformat(),
            "difficulty_profile_id": difficulty_profile.profile_id
        })

        return scaled_challenge

    def create_progression_plan(self, agent_profile: AgentProfile,
                              target_skills: List[str],
                              time_horizon_days: int = 30) -> ProgressionPlan:
        """Create personalized progression plan"""

        self.logger.info(f"📋 Creating progression plan for agent {agent_profile.agent_id}")

        # Assess current skill levels
        current_skills = {}
        for skill in target_skills:
            if skill in agent_profile.skill_levels:
                current_skills[skill] = agent_profile.skill_levels[skill]
            else:
                current_skills[skill] = 0.3  # Default for unknown skills

        # Design progression path
        progression_path = []
        estimated_timeline = {}

        for skill in target_skills:
            current_level = current_skills[skill]
            target_level = 0.8  # Target proficiency

            if current_level >= target_level:
                estimated_timeline[skill] = 0  # Already proficient
                continue

            # Estimate learning trajectory
            skill_gap = target_level - current_level

            # Base learning rate (can be personalized)
            base_learning_rate = 0.05  # 5% improvement per challenge

            # Adjust for agent's historical learning velocity
            if agent_profile.agent_id in self.progression_tracker.skill_assessments:
                agent_skills = self.progression_tracker.skill_assessments[agent_profile.agent_id]
                if skill in agent_skills:
                    learning_velocity = agent_skills[skill].learning_velocity
                    base_learning_rate *= max(0.5, 1.0 + learning_velocity)

            # Estimate challenges needed
            challenges_needed = max(1, int(skill_gap / base_learning_rate))

            # Estimate days (assuming 1-2 challenges per day)
            days_needed = min(time_horizon_days, challenges_needed // 1.5)
            estimated_timeline[skill] = int(days_needed)

            # Create progression steps
            progression_path.append({
                "skill": skill,
                "current_level": current_level,
                "target_level": target_level,
                "estimated_challenges": challenges_needed,
                "progression_steps": self._create_skill_progression_steps(skill, current_level, target_level)
            })

        # Identify next milestones
        next_milestones = []
        for step in progression_path:
            if step["current_level"] < 0.5:
                next_milestones.append(f"Achieve basic proficiency in {step['skill']}")
            elif step["current_level"] < 0.8:
                next_milestones.append(f"Advance to intermediate level in {step['skill']}")

        plan = ProgressionPlan(
            agent_id=agent_profile.agent_id,
            current_stage="skill_development",
            target_skills=target_skills,
            progression_path=progression_path,
            estimated_timeline=estimated_timeline,
            next_milestones=next_milestones,
            adaptive_parameters={
                "base_learning_rate": base_learning_rate,
                "time_horizon_days": time_horizon_days,
                "zpd_preference": (self.zpd_lower_bound + self.zpd_upper_bound) / 2
            }
        )

        return plan

    def _create_skill_progression_steps(self, skill: str, current_level: float, target_level: float) -> List[Dict[str, Any]]:
        """Create detailed progression steps for a skill"""
        steps = []
        step_size = (target_level - current_level) / 5  # 5 steps to target

        milestones = [
            "Basic understanding",
            "Practical application",
            "Problem-solving competency",
            "Advanced application",
            "Mastery achievement"
        ]

        for i in range(5):
            step_level = current_level + (i + 1) * step_size
            steps.append({
                "step_number": i + 1,
                "milestone": milestones[i],
                "target_level": min(target_level, step_level),
                "recommended_challenges": max(1, int(step_size / 0.05)),  # Challenges per step
                "focus_areas": self._get_skill_focus_areas(skill, step_level)
            })

        return steps

    def _get_skill_focus_areas(self, skill: str, level: float) -> List[str]:
        """Get focus areas for skill development at specific level"""
        focus_areas = {
            "basic_syntax": {
                0.3: ["variable assignment", "basic operators"],
                0.5: ["control structures", "function calls"],
                0.7: ["data types", "error handling"],
                0.9: ["advanced syntax", "best practices"]
            },
            "algorithms": {
                0.3: ["understanding concepts", "tracing execution"],
                0.5: ["implementing basic algorithms", "analyzing complexity"],
                0.7: ["optimizing algorithms", "comparing approaches"],
                0.9: ["designing new algorithms", "advanced optimization"]
            },
            "problem_solving": {
                0.3: ["problem decomposition", "pattern recognition"],
                0.5: ["solution planning", "step-by-step implementation"],
                0.7: ["multiple solution approaches", "trade-off analysis"],
                0.9: ["creative problem solving", "novel approaches"]
            }
        }

        skill_focuses = focus_areas.get(skill, {})

        # Find the appropriate level
        for threshold in sorted(skill_focuses.keys()):
            if level <= threshold:
                return skill_focuses[threshold]

        # Default if no specific focus areas defined
        return ["general practice", "skill reinforcement"]

    def get_scaling_statistics(self) -> Dict[str, Any]:
        """Get statistics about difficulty scaling operations"""
        return {
            "total_agents_tracked": len(self.progression_tracker.skill_assessments),
            "skills_assessed": sum(len(skills) for skills in self.progression_tracker.skill_assessments.values()),
            "scaling_parameters": {
                "zpd_lower_bound": self.zpd_lower_bound,
                "zpd_upper_bound": self.zpd_upper_bound
            },
            "difficulty_dimensions": list(self.multi_dimensional_difficulty.dimension_definitions.keys())
        }